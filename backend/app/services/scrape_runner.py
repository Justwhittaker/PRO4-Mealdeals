"""Run scrapers safely from sync Celery workers or async FastAPI handlers."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.scrapers.global_retail import (
    GlobalRetailScraper,
    TARGET_MARKETS,
    iter_market_areas,
)
from app.scrapers.zones import markets_for_zone
from app.services.ingest import (
    ingest_scraped_deals,
    normalize_city,
    normalize_country,
)
from app.services.marketing_contacts import ingest_marketing_contacts_from_deals
from app.services.scrape_report import (
    breakdown_from_scraped_deals,
    build_scrape_report,
    merge_breakdown_rows,
)

logger = logging.getLogger(__name__)

_settings = get_settings()
_engine = create_engine(_settings.database_url_sync, pool_pre_ping=True)
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _run_coro(coro: Any) -> Any:
    """Run an async coroutine from sync code, even if an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def scrape_and_ingest_area(country_code: str, city: str) -> dict[str, int | str]:
    """Scrape + persist deals for one city. Safe to call from FastAPI or Celery."""
    country = normalize_country(country_code)
    city_name = normalize_city(city)
    scraper = GlobalRetailScraper()

    async def _run() -> list:
        return await scraper.scrape(country, city_name)

    deals = _run_coro(_run())
    with _Session() as session:
        ingested = ingest_scraped_deals(session, deals)
        contacts = ingest_marketing_contacts_from_deals(session, deals)
    return {
        "country_code": country,
        "city": city_name,
        "discovered": len(deals),
        "ingested": ingested,
        "marketing_contacts": contacts,
    }


def scrape_and_ingest_markets(
    country_codes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Scrape every configured city for the given markets (default: worldwide targets).

    Reuses one scraper instance so live merchant HTML is cached across cities.
    Returns run counters plus a full report payload for the /scrape skill.
    """
    started = time.perf_counter()
    markets = country_codes or list(TARGET_MARKETS)
    areas = iter_market_areas(markets)
    scraper = GlobalRetailScraper()
    discovered = 0
    ingested = 0
    contacts = 0
    by_country: dict[str, int] = {code: 0 for code in markets}
    breakdown_batches: list[list[dict[str, Any]]] = []

    async def _scrape_all() -> list[tuple[str, str, list]]:
        out: list[tuple[str, str, list]] = []
        for country, city in areas:
            deals = await scraper.scrape(country, city)
            out.append((country, city, deals))
        return out

    batches = _run_coro(_scrape_all())
    with _Session() as session:
        for country, city, deals in batches:
            discovered += len(deals)
            count = ingest_scraped_deals(session, deals)
            contact_count = ingest_marketing_contacts_from_deals(session, deals)
            ingested += count
            contacts += contact_count
            by_country[country] = by_country.get(country, 0) + count
            breakdown_batches.append(breakdown_from_scraped_deals(deals))
            logger.info(
                "%s/%s: discovered=%s ingested=%s contacts=%s",
                country,
                city,
                len(deals),
                count,
                contact_count,
            )

        runtime_seconds = round(time.perf_counter() - started, 1)
        report = build_scrape_report(
            session,
            discovered=discovered,
            ingested=ingested,
            marketing_contacts_upserted=contacts,
            runtime_seconds=runtime_seconds,
            markets=markets,
            run_breakdown=merge_breakdown_rows(breakdown_batches),
        )

    return {
        "areas": len(areas),
        "markets": len(markets),
        "discovered": discovered,
        "ingested": ingested,
        "marketing_contacts": contacts,
        "marketing_contacts_unique": report["summary"]["marketing_contacts_unique"],
        "runtime_seconds": runtime_seconds,
        "by_country": by_country,
        "breakdown": report["breakdown"],
        "category_tally": report["category_tally"],
        "report": report,
    }


def scrape_and_ingest_zone(zone_id: str) -> dict[str, Any]:
    """
    Bite-size continental scrape: one of eight zones (hub cities only).

    Celery Beat fires these every 15 minutes within each 6-hour cycle so a
    full worldwide refresh completes in ~2 hours without one giant job.
    """
    markets = markets_for_zone(zone_id)
    if not markets:
        raise ValueError(f"Unknown or empty scrape zone: {zone_id}")
    return scrape_and_ingest_markets(markets)
