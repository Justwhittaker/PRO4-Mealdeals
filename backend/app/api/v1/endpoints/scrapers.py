"""Trigger area scrapers (auto-skim deals for a city)."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.scrapers.global_retail import NEW_MARKETS, TARGET_MARKETS, iter_market_areas
from app.services.scrape_report import build_scrape_report
from app.services.scrape_runner import scrape_and_ingest_area, scrape_and_ingest_markets
from app.workers.tasks import scrape_area as scrape_area_task
from app.workers.tasks import scrape_global_retail as scrape_global_task

_settings = get_settings()
_report_engine = create_engine(_settings.database_url_sync, pool_pre_ping=True)
_ReportSession = sessionmaker(bind=_report_engine, autocommit=False, autoflush=False)

router = APIRouter(prefix="/scrapers", tags=["scrapers"])


class BreakdownRow(BaseModel):
    country: str
    city: str
    category: str
    deals: int


class CategoryTallyRow(BaseModel):
    category: str
    deals: int


class ScrapeSummary(BaseModel):
    areas: int
    markets: int
    market_codes: list[str] | None = None
    deals_discovered: int
    deals_ingested: int
    marketing_contacts_upserted: int
    marketing_contacts_unique: int
    runtime_seconds: float | None = None
    active_deals_in_db: int | None = None


class ScrapeReport(BaseModel):
    summary: ScrapeSummary
    by_country: dict[str, int]
    breakdown: list[BreakdownRow]
    category_tally: list[CategoryTallyRow]


class ScrapeAreaResponse(BaseModel):
    status: str
    country_code: str
    city: str
    discovered: int | None = None
    ingested: int | None = None
    message: str


class ScrapeWorldwideResponse(BaseModel):
    status: str
    markets: list[str]
    areas: int
    discovered: int | None = None
    ingested: int | None = None
    marketing_contacts: int | None = None
    marketing_contacts_unique: int | None = None
    runtime_seconds: float | None = None
    by_country: dict[str, int] | None = None
    breakdown: list[BreakdownRow] | None = None
    category_tally: list[CategoryTallyRow] | None = None
    report: ScrapeReport | None = None
    message: str


def _report_from_result(result: dict[str, Any]) -> ScrapeReport | None:
    raw = result.get("report")
    if not isinstance(raw, dict):
        return None
    return ScrapeReport.model_validate(raw)


def _celery_workers_online() -> bool:
    """True only if at least one Celery worker responds to ping."""
    try:
        from app.workers.celery_app import celery_app

        replies = celery_app.control.ping(timeout=1.0)
        return bool(replies)
    except Exception:
        return False


def _queue_or_background(
    background_tasks: BackgroundTasks,
    *,
    celery_delay,
    background_fn,
    background_args: tuple[Any, ...],
) -> str:
    """
    Enqueue via Celery when a worker is live; otherwise run in-process after
    the response. Publishing to Redis alone is not enough (no worker = stuck).
    """
    if _celery_workers_online():
        try:
            celery_delay()
            return "celery"
        except Exception:
            pass
    background_tasks.add_task(background_fn, *background_args)
    return "background"


@router.post("/area", response_model=ScrapeAreaResponse)
async def scrape_area_endpoint(
    background_tasks: BackgroundTasks,
    country_code: str = Query(..., min_length=2, max_length=3),
    city: str = Query(..., min_length=1, max_length=100),
    wait: bool = Query(
        default=True,
        description="If true, scrape synchronously and return counts; else queue Celery/background.",
    ),
) -> ScrapeAreaResponse:
    """
    Skim public promo sources for a city and persist external deals.

    City pages call this when the feed is empty so the area auto-fills.
    """
    if wait:
        result = await asyncio.to_thread(scrape_and_ingest_area, country_code, city)
        return ScrapeAreaResponse(
            status="completed",
            country_code=str(result["country_code"]),
            city=str(result["city"]),
            discovered=int(result["discovered"]),
            ingested=int(result["ingested"]),
            message="Area scrape finished and deals were ingested.",
        )

    # Prefer Celery only when a worker is actually online; otherwise BackgroundTasks.
    queued_via = _queue_or_background(
        background_tasks,
        celery_delay=lambda: scrape_area_task.delay(country_code, city),
        background_fn=scrape_and_ingest_area,
        background_args=(country_code, city),
    )

    return ScrapeAreaResponse(
        status="queued",
        country_code=country_code.upper(),
        city=city,
        message=f"Area scrape queued via {queued_via}.",
    )


async def _run_worldwide_scrape(
    background_tasks: BackgroundTasks,
    *,
    wait: bool,
    only_new: bool,
) -> ScrapeWorldwideResponse:
    markets = list(NEW_MARKETS if only_new else TARGET_MARKETS)
    areas = len(iter_market_areas(markets))

    if wait:
        result = await asyncio.to_thread(scrape_and_ingest_markets, markets)
        by_country = result.get("by_country")
        report = _report_from_result(result)
        return ScrapeWorldwideResponse(
            status="completed",
            markets=markets,
            areas=int(result["areas"]),
            discovered=int(result["discovered"]),
            ingested=int(result["ingested"]),
            marketing_contacts=(
                int(result["marketing_contacts"])
                if result.get("marketing_contacts") is not None
                else None
            ),
            marketing_contacts_unique=(
                int(result["marketing_contacts_unique"])
                if result.get("marketing_contacts_unique") is not None
                else None
            ),
            runtime_seconds=(
                float(result["runtime_seconds"])
                if result.get("runtime_seconds") is not None
                else None
            ),
            by_country=(
                {str(k): int(v) for k, v in by_country.items()}
                if isinstance(by_country, dict)
                else None
            ),
            breakdown=report.breakdown if report else None,
            category_tally=report.category_tally if report else None,
            report=report,
            message="Worldwide scrape finished; deals + marketing contacts ingested.",
        )

    queued_via = _queue_or_background(
        background_tasks,
        celery_delay=lambda: scrape_global_task.delay(markets),
        background_fn=scrape_and_ingest_markets,
        background_args=(markets,),
    )

    return ScrapeWorldwideResponse(
        status="queued",
        markets=markets,
        areas=areas,
        message=(
            f"Worldwide scrape queued via {queued_via} "
            f"({len(markets)} markets / {areas} cities)."
        ),
    )


@router.post("/worldwide", response_model=ScrapeWorldwideResponse)
async def scrape_worldwide_endpoint(
    background_tasks: BackgroundTasks,
    wait: bool = Query(
        default=False,
        description="If true, run synchronously (can take several minutes).",
    ),
    only_new: bool = Query(
        default=False,
        description="If true, scrape only markets added after the initial seed pass.",
    ),
) -> ScrapeWorldwideResponse:
    """Scrape major cities across configured worldwide target markets."""
    return await _run_worldwide_scrape(
        background_tasks, wait=wait, only_new=only_new
    )


@router.post("/scrape", response_model=ScrapeWorldwideResponse)
async def scrape_fresh_endpoint(
    background_tasks: BackgroundTasks,
    wait: bool = Query(
        default=True,
        description="If true, run synchronously and return the full results report.",
    ),
) -> ScrapeWorldwideResponse:
    """
    Fresh hospitality scrape refresh (used by the `/scrape` Cursor skill).

    Applies the hospitality deal-scraping rule across all TARGET_MARKETS,
    upserts deals, and saves business name/phone/email into marketing_contacts.
    Defaults to wait=true so the skill can render the results breakdown.
    """
    return await _run_worldwide_scrape(
        background_tasks, wait=wait, only_new=False
    )


def _load_scrape_report() -> dict[str, Any]:
    with _ReportSession() as session:
        return build_scrape_report(session, markets=list(TARGET_MARKETS))


@router.get("/report", response_model=ScrapeReport)
async def scrape_report_endpoint() -> ScrapeReport:
    """
    Current scrape inventory report (areas/markets/deals/contacts + breakdowns).

    Use after an async scrape completes, or anytime for a live DB snapshot.
    """
    report = await asyncio.to_thread(_load_scrape_report)
    return ScrapeReport.model_validate(report)


class PlanInfo(BaseModel):
    name: str = "Priority Slots"
    intro_price_eur: float = 20
    intro_months: int = 3
    intro_deal_slots: int = 3
    recurring_price_eur: float = 20
    recurring_interval: str = "month"
    recurring_deal_slots: int = 3
    summary: str = Field(
        default=(
            "€20 for 3 months with 3 priority deal slots, "
            "then €20/month still with 3 slots. "
            "Subscriber deals rank above scraped external listings."
        )
    )


@router.get("/plans/priority", response_model=PlanInfo)
async def priority_plan_info() -> PlanInfo:
    """Public plan copy for the merchant portal."""
    return PlanInfo()
