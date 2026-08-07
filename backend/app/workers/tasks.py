"""Celery tasks for currency updates and area deal scraping."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.currency import Currency
from app.models.newsletter import NewsletterSubscriber
from app.scrapers.global_retail import TARGET_MARKETS, iter_market_areas
from app.scrapers.markets import CURRENCY_RATES
from app.services.newsletter import send_weekly_special_to_subscriber
from app.services.scrape_runner import scrape_and_ingest_area, scrape_and_ingest_markets
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)

_STUB_RATES: dict[str, tuple[str, str]] = CURRENCY_RATES


@celery_app.task(name="app.workers.tasks.update_currency_rates")
def update_currency_rates() -> dict[str, str]:
    """Upsert FX rates into `currencies` (stub table; swap for live provider later)."""
    updated: dict[str, str] = {}
    with SyncSessionLocal() as session:
        for code, (rate, symbol) in _STUB_RATES.items():
            row = session.get(Currency, code)
            if row is None:
                session.add(
                    Currency(code=code, usd_rate=Decimal(rate), symbol=symbol)
                )
            else:
                row.usd_rate = Decimal(rate)
                row.symbol = symbol
            updated[code] = rate
        session.commit()
    logger.info("Updated %d currency rates", len(updated))
    return updated


@celery_app.task(name="app.workers.tasks.scrape_area")
def scrape_area(country_code: str, city: str) -> dict[str, int | str]:
    """Scrape + persist deals for a single city/country."""
    result = scrape_and_ingest_area(country_code, city)
    logger.info("Area scrape complete: %s", result)
    return result


@celery_app.task(name="app.workers.tasks.scrape_global_retail")
def scrape_global_retail(country_codes: list[str] | None = None) -> dict[str, int]:
    """Periodic scrape across all configured cities for target markets."""
    markets = country_codes or list(TARGET_MARKETS)
    result = scrape_and_ingest_markets(markets)
    logger.info(
        "Worldwide scrape complete: areas=%s discovered=%s ingested=%s",
        result.get("areas"),
        result.get("discovered"),
        result.get("ingested"),
    )
    # Keep a compact per-country rollup for beat/task return values.
    counts: dict[str, int] = {code: 0 for code in markets}
    for country, _city in iter_market_areas(markets):
        # Counts are filled from detailed results when present.
        counts.setdefault(country, 0)
    by_country = result.get("by_country")
    if isinstance(by_country, dict):
        for code, ingested in by_country.items():
            counts[str(code)] = int(ingested)
    return counts


@celery_app.task(name="app.workers.tasks.send_weekly_specials")
def send_weekly_specials() -> dict[str, int]:
    """Friday job: email active newsletter subscribers current deals."""
    sent = 0
    skipped = 0
    failed = 0
    with SyncSessionLocal() as session:
        subscribers = list(
            session.scalars(
                select(NewsletterSubscriber).where(
                    NewsletterSubscriber.is_subscribed.is_(True)
                )
            ).all()
        )
        for subscriber in subscribers:
            result = send_weekly_special_to_subscriber(session, subscriber)
            if result.get("skipped"):
                skipped += 1
            elif result.get("sent"):
                sent += 1
            else:
                failed += 1
    summary = {"sent": sent, "skipped": skipped, "failed": failed}
    logger.info("Weekly specials complete: %s", summary)
    return summary


@celery_app.task(name="app.workers.tasks.ping")
def ping() -> str:
    return "pong"
