"""Celery tasks for currency updates and area deal scraping."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.models.currency import Currency
from app.models.newsletter import NewsletterSubscriber
from app.scrapers.global_retail import TARGET_MARKETS, iter_market_areas
from app.scrapers.markets import CURRENCY_RATES
from app.services.deal_expiry import expire_past_due_deals
from app.services.merchant_outreach import send_merchant_outreach_batch
from app.services.newsletter import send_weekly_special_to_subscriber
from app.services.scrape_cycle_digest import (
    queue_failed_city_retries,
    run_city_retry,
    run_scrape_cycle_digest,
)
from app.services.scrape_cycle_stats import (
    cycle_id_for_start,
    cycle_id_from_task_request,
    cycle_start_for_time,
    record_zone_result,
    zone_already_succeeded,
)
from app.services.scrape_runner import (
    scrape_and_ingest_area,
    scrape_and_ingest_markets,
    scrape_and_ingest_zone,
    scrape_progress_of,
)
from app.scrapers.zones import (
    SCRAPE_QUEUE,
    SCRAPE_ZONES,
    ZONE_TASK_SOFT_TIME_LIMIT_SECONDS,
    ZONE_TASK_TIME_LIMIT_SECONDS,
    markets_for_zone,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=_sync_engine, autocommit=False, autoflush=False)

_STUB_RATES: dict[str, tuple[str, str]] = CURRENCY_RATES


@celery_app.task(name="app.workers.tasks.expire_past_due_deals")
def expire_past_due_deals_task() -> dict[str, int]:
    """Hourly: hide scraped deals past expires_at from the public feed."""
    from app.services.frontend_revalidate import revalidate_after_scrape

    with SyncSessionLocal() as session:
        count = expire_past_due_deals(session)
    if count > 0:
        revalidate_after_scrape(areas=set())
    return {"expired": count}


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


_PROGRESS_KEYS = (
    "areas",
    "areas_total",
    "discovered",
    "ingested",
    "stale_deactivated",
    "marketing_contacts",
    "revalidate_ok",
    "revalidate_fail",
    "cities_failed",
    "cities_completed",
    "cities_not_reached",
)


def _zone_failure_payload(
    zone: str,
    error: str,
    *,
    started_at: str,
) -> dict[str, Any]:
    return {
        "zone": zone,
        "label": SCRAPE_ZONES[zone]["label"],
        "ok": False,
        "status": "failed",
        "error": error[:500],
        "started_at": started_at,
        "areas": 0,
        "discovered": 0,
        "ingested": 0,
        "stale_deactivated": 0,
        "marketing_contacts": 0,
        "revalidate_ok": 0,
        "revalidate_fail": 0,
        "cities_failed": [],
    }


def _queued_cycle_id(request: Any) -> str:
    stamped = cycle_id_from_task_request(request)
    if stamped:
        return stamped
    return cycle_id_for_start(cycle_start_for_time())


@celery_app.task(
    bind=True,
    name="app.workers.tasks.scrape_zone_retail",
    acks_late=True,
    reject_on_worker_lost=True,
    acks_on_failure_or_timeout=True,
    soft_time_limit=ZONE_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=ZONE_TASK_TIME_LIMIT_SECONDS,
)
def scrape_zone_retail(self: Any, zone_id: str) -> dict[str, Any]:
    """Continental bite-size scrape for one worldwide zone.

    Acked late so a dead worker redelivers the zone, but the hard time limit
    is shorter than the Redis visibility timeout so a live run is not
    delivered a second time. A cycle that already recorded success is skipped
    when a late restore arrives after the zone finished.
    """
    zone = zone_id.strip().lower()
    if zone not in SCRAPE_ZONES:
        # A rename leaves old messages on the queue. Ack them as a no-op so
        # the worker does not record a crash for a zone it no longer runs.
        logger.warning("Unknown scrape zone %r; skipping", zone_id)
        return {
            "zone": zone,
            "ok": True,
            "status": "skipped",
            "skipped": "unknown_zone",
        }
    cycle_id = _queued_cycle_id(self.request)
    if zone_already_succeeded(cycle_id, zone):
        logger.info(
            "Zone %s already completed for cycle %s; skipping redelivery",
            zone,
            cycle_id,
        )
        return {
            "zone": zone,
            "ok": True,
            "status": "completed",
            "skipped": "already_completed",
            "cycle_id": cycle_id,
        }

    started_at = datetime.now(timezone.utc).isoformat()
    running = {
        "ok": False,
        "status": "running",
        "started_at": started_at,
        "areas": 0,
        "discovered": 0,
        "ingested": 0,
        "stale_deactivated": 0,
        "marketing_contacts": 0,
        "revalidate_ok": 0,
        "revalidate_fail": 0,
    }
    hostname = getattr(self.request, "hostname", None)
    if hostname:
        running["worker_hostname"] = str(hostname)
    record_zone_result(zone, running, cycle_id=cycle_id)
    try:
        result = scrape_and_ingest_zone(zone)
    except SoftTimeLimitExceeded as exc:
        summary = _zone_failure_payload(
            zone,
            "soft time limit exceeded",
            started_at=started_at,
        )
        summary["status"] = "timed_out"
        summary["ok"] = False
        progress = scrape_progress_of(exc)
        for key in _PROGRESS_KEYS:
            if key in progress:
                summary[key] = progress[key]
        record_zone_result(zone, summary, cycle_id=cycle_id)
        logger.error(
            "Zone scrape hit soft time limit (%s) cycle=%s areas=%s/%s discovered=%s ingested=%s not_reached=%s",
            zone,
            cycle_id,
            summary.get("areas"),
            summary.get("areas_total"),
            summary.get("discovered"),
            summary.get("ingested"),
            len(summary.get("cities_not_reached") or []),
        )
        return summary
    except Exception as exc:
        summary = _zone_failure_payload(zone, str(exc), started_at=started_at)
        record_zone_result(zone, summary, cycle_id=cycle_id)
        raise
    markets = markets_for_zone(zone)
    cities_failed = result.get("cities_failed") or []
    if not isinstance(cities_failed, list):
        cities_failed = []
    areas = int(result.get("areas") or 0)
    every_city_failed = areas > 0 and len(cities_failed) >= areas
    summary = {
        "zone": zone,
        "label": SCRAPE_ZONES[zone]["label"],
        "areas": areas,
        "discovered": int(result.get("discovered") or 0),
        "ingested": int(result.get("ingested") or 0),
        "stale_deactivated": int(result.get("stale_deactivated") or 0),
        "marketing_contacts": int(result.get("marketing_contacts") or 0),
        "revalidate_ok": int(result.get("revalidate_ok") or 0),
        "revalidate_fail": int(result.get("revalidate_fail") or 0),
        "markets": len(markets),
        "cities_failed": cities_failed,
        "ok": not every_city_failed,
        "status": "failed" if every_city_failed else "completed",
        "started_at": started_at,
        "cycle_id": cycle_id,
    }
    if every_city_failed:
        summary["error"] = "every city in the zone failed"
    record_zone_result(zone, summary, cycle_id=cycle_id)
    logger.info(
        "Zone scrape complete (%s) cycle=%s: areas=%s discovered=%s ingested=%s cities_failed=%s",
        zone,
        cycle_id,
        summary["areas"],
        summary["discovered"],
        summary["ingested"],
        len(cities_failed),
    )
    return summary


def _enqueue_city_retry(cycle_id: str, country: str, city: str) -> None:
    retry_failed_scrape_city.apply_async(
        args=[cycle_id, country, city],
        queue=SCRAPE_QUEUE,
    )


@celery_app.task(name="app.workers.tasks.retry_failed_scrape_city")
def retry_failed_scrape_city(
    cycle_id: str,
    country_code: str,
    city: str,
) -> dict[str, Any]:
    """One scrape of a city that failed earlier in this cycle. Never re-queues."""
    return run_city_retry(
        cycle_id,
        country_code,
        city,
        scrape=scrape_and_ingest_area,
    )


@celery_app.task(name="app.workers.tasks.send_scrape_cycle_digest")
def send_scrape_cycle_digest() -> dict[str, object]:
    """Twice-daily ntfy: zone %, site transfer, deals, emails, categories.

    After the digest is sent, each city in ``cities_failed`` is queued once.
    Retry results arrive as a short follow-up ntfy when those tasks finish.
    The maintenance worker stays free instead of waiting on city scrapes.
    """
    result = run_scrape_cycle_digest()
    report = result["report"]
    cycle_results = report.get("cycle_results")
    if not isinstance(cycle_results, dict):
        cycle_results = {}
    try:
        queued = queue_failed_city_retries(
            str(report["cycle_id"]),
            cycle_results,
            enqueue=_enqueue_city_retry,
        )
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception(
            "Failed to queue city retries for cycle %s",
            report.get("cycle_id"),
        )
        queued = []
    return {
        "cycle_id": report["cycle_id"],
        "zones_pct": report["zones"]["pct_completed"],
        "new_deals": report["new_deals"],
        "dropped_deals": report["dropped_deals"],
        "net_new_emails": report["net_new_emails"],
        "ntfy": result["ntfy"],
        "city_retries_queued": len(queued),
    }


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


@celery_app.task(name="app.workers.tasks.send_merchant_outreach")
def send_merchant_outreach() -> dict[str, int]:
    """Monthly batch: email scraped businesses about free listing + priority slots."""
    with SyncSessionLocal() as session:
        return send_merchant_outreach_batch(session)


@celery_app.task(name="app.workers.tasks.ping")
def ping() -> str:
    return "pong"
