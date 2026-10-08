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
from app.core.task_errors import is_fatal_task_error
from app.scrapers.global_retail import (
    GlobalRetailScraper,
    TARGET_MARKETS,
    iter_market_areas,
)
from app.scrapers.zones import iter_zone_areas
from app.services.frontend_revalidate import revalidate_after_scrape
from app.services.ingest import (
    ingest_hub_scrape,
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


def _live_revalidate(country: str, city: str, *, ingested: int, stale: int) -> dict[str, Any]:
    """Bust site cache after each hub so new deals appear while the zone still runs."""
    if ingested <= 0 and stale <= 0:
        return {"skipped": True, "reason": "no_changes"}
    result = revalidate_after_scrape(areas={(country, city)})
    logger.info(
        "Live revalidate %s/%s ingested=%s stale=%s → %s",
        country,
        city,
        ingested,
        stale,
        result,
    )
    return result


def scrape_and_ingest_area(country_code: str, city: str) -> dict[str, int | str]:
    """Scrape + persist deals for one city. Safe to call from FastAPI or Celery."""
    country = normalize_country(country_code)
    city_name = normalize_city(city)
    scraper = GlobalRetailScraper()

    async def _run() -> list:
        return await scraper.scrape(country, city_name)

    deals = _run_coro(_run())
    with _Session() as session:
        hub_result = ingest_hub_scrape(session, country, city_name, deals)
        contacts = ingest_marketing_contacts_from_deals(session, deals)
    revalidate = _live_revalidate(
        country,
        city_name,
        ingested=hub_result["ingested"],
        stale=hub_result["stale_deactivated"],
    )
    return {
        "country_code": country,
        "city": city_name,
        "discovered": len(deals),
        "ingested": hub_result["ingested"],
        "stale_deactivated": hub_result["stale_deactivated"],
        "marketing_contacts": contacts,
        "frontend_revalidate": revalidate,
    }


def _city_ref(country: str, city: str) -> dict[str, str]:
    return {"country": country, "city": city}


def scrape_progress_of(exc: BaseException) -> dict[str, Any]:
    """Partial zone totals attached when a time limit aborts the city loop."""
    raw = getattr(exc, "scrape_progress", None)
    if isinstance(raw, dict):
        return raw
    return {}


def _snapshot_progress(progress: dict[str, Any]) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for key, value in progress.items():
        snap[key] = list(value) if isinstance(value, list) else value
    return snap


def scrape_and_ingest_areas(
    areas: list[tuple[str, str]],
    markets: list[str],
) -> dict[str, Any]:
    """Scrape the given hubs. A time limit keeps the totals gathered so far."""
    progress: dict[str, Any] = {
        "areas": 0,
        "areas_total": len(areas),
        "discovered": 0,
        "ingested": 0,
        "stale_deactivated": 0,
        "marketing_contacts": 0,
        "revalidate_ok": 0,
        "revalidate_fail": 0,
        "cities_failed": [],
        "cities_completed": [],
        "cities_not_reached": [_city_ref(country, city) for country, city in areas],
    }
    try:
        return _scrape_areas(areas, markets, progress)
    except Exception as exc:
        if is_fatal_task_error(exc):
            setattr(exc, "scrape_progress", _snapshot_progress(progress))
        raise


def _scrape_areas(
    areas: list[tuple[str, str]],
    markets: list[str],
    progress: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    scraper = GlobalRetailScraper()
    discovered = 0
    ingested = 0
    stale_total = 0
    contacts = 0
    by_country: dict[str, int] = {code: 0 for code in markets}
    breakdown_batches: list[list[dict[str, Any]]] = []
    revalidate_runs = 0
    revalidate_ok = 0
    revalidate_fail = 0
    cities_failed: list[dict[str, str]] = []
    cities_completed: list[dict[str, str]] = []

    for index, (country, city) in enumerate(areas):
        progress["areas"] = len(cities_completed) + len(cities_failed)
        progress["cities_completed"] = list(cities_completed)
        progress["cities_failed"] = list(cities_failed)
        progress["cities_not_reached"] = [
            _city_ref(c, t) for c, t in areas[index:]
        ]
        progress["discovered"] = discovered
        progress["ingested"] = ingested
        progress["stale_deactivated"] = stale_total
        progress["marketing_contacts"] = contacts
        progress["revalidate_ok"] = revalidate_ok
        progress["revalidate_fail"] = revalidate_fail
        try:
            async def _run(c: str = country, t: str = city) -> list:
                return await scraper.scrape(c, t)

            deals = _run_coro(_run())
            discovered += len(deals)

            with _Session() as session:
                hub_result = ingest_hub_scrape(session, country, city, deals)

            count = hub_result["ingested"]
            stale = hub_result["stale_deactivated"]
            ingested += count
            stale_total += stale
            by_country[country] = by_country.get(country, 0) + count
            breakdown_batches.append(breakdown_from_scraped_deals(deals))
            cities_completed.append(_city_ref(country, city))
            progress["areas"] = len(cities_completed) + len(cities_failed)
            progress["cities_completed"] = list(cities_completed)
            progress["cities_not_reached"] = [
                _city_ref(c, t) for c, t in areas[index + 1 :]
            ]
            progress["discovered"] = discovered
            progress["ingested"] = ingested
            progress["stale_deactivated"] = stale_total

            with _Session() as session:
                contact_count = ingest_marketing_contacts_from_deals(session, deals)
            contacts += contact_count
            progress["marketing_contacts"] = contacts

            revalidate = _live_revalidate(
                country, city, ingested=count, stale=stale
            )
            if not revalidate.get("skipped"):
                revalidate_runs += 1
                if revalidate.get("ok") is True:
                    revalidate_ok += 1
                elif revalidate.get("ok") is False:
                    revalidate_fail += 1
            progress["revalidate_ok"] = revalidate_ok
            progress["revalidate_fail"] = revalidate_fail

            logger.info(
                "%s/%s: discovered=%s ingested=%s stale=%s contacts=%s",
                country,
                city,
                len(deals),
                count,
                stale,
                contact_count,
            )
        except Exception as exc:
            if is_fatal_task_error(exc):
                raise
            logger.exception(
                "City scrape failed %s/%s (remaining cities continue): %s",
                country,
                city,
                exc,
            )
            cities_failed.append(
                {
                    "country": country,
                    "city": city,
                    "error": str(exc)[:500],
                }
            )

    progress["areas"] = len(cities_completed) + len(cities_failed)
    progress["cities_completed"] = list(cities_completed)
    progress["cities_failed"] = list(cities_failed)
    progress["cities_not_reached"] = []
    progress["discovered"] = discovered
    progress["ingested"] = ingested
    progress["stale_deactivated"] = stale_total
    progress["marketing_contacts"] = contacts
    progress["revalidate_ok"] = revalidate_ok
    progress["revalidate_fail"] = revalidate_fail

    runtime_seconds = round(time.perf_counter() - started, 1)
    with _Session() as session:
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
        "areas_total": len(areas),
        "markets": len(markets),
        "discovered": discovered,
        "ingested": ingested,
        "stale_deactivated": stale_total,
        "marketing_contacts": contacts,
        "marketing_contacts_unique": report["summary"]["marketing_contacts_unique"],
        "runtime_seconds": runtime_seconds,
        "by_country": by_country,
        "breakdown": report["breakdown"],
        "category_tally": report["category_tally"],
        "report": report,
        "frontend_revalidate_runs": revalidate_runs,
        "revalidate_ok": revalidate_ok,
        "revalidate_fail": revalidate_fail,
        "cities_failed": cities_failed,
        "cities_completed": cities_completed,
        "cities_not_reached": [],
    }


def scrape_and_ingest_markets(
    country_codes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Scrape every configured city for the given markets (default: worldwide targets).

    Processes hub-by-hub: scrape → ingest → drop stale → revalidate the site live.
    """
    markets = country_codes or list(TARGET_MARKETS)
    return scrape_and_ingest_areas(iter_market_areas(markets), markets)


def scrape_and_ingest_zone(zone_id: str) -> dict[str, Any]:
    """Scrape one beat zone. Cities are only those assigned to the zone."""
    areas = iter_zone_areas(zone_id)
    if not areas:
        raise ValueError(f"Unknown or empty scrape zone: {zone_id}")
    markets = sorted({country for country, _city in areas})
    return scrape_and_ingest_areas(areas, markets)
