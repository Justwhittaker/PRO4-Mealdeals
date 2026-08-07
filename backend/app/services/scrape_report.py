"""Build scrape result reports (summary + country/city/category breakdowns)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.deal import Deal
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant
from app.scrapers.base import ScrapedDeal
from app.scrapers.categories import CATEGORY_ORDER, categorize_venue
from app.scrapers.markets import MARKET_CITIES, TARGET_MARKETS


def breakdown_from_scraped_deals(
    deals: Sequence[ScrapedDeal],
) -> list[dict[str, Any]]:
    """Country → city → category deal counts from a scrape batch."""
    counter: Counter[tuple[str, str, str]] = Counter()
    for deal in deals:
        country = (deal.country_code or "??").upper()
        city = deal.city or "Unknown"
        category = deal.venue_category or categorize_venue(deal.merchant_name)
        counter[(country, city, category)] += 1
    return _rows_from_counter(counter)


def _rows_from_counter(
    counter: Counter[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "country": country,
            "city": city,
            "category": category,
            "deals": count,
        }
        for (country, city, category), count in sorted(
            counter.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2]),
        )
    ]


def _category_tally_rows(tally: Counter[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for category in CATEGORY_ORDER:
        if tally.get(category):
            rows.append({"category": category, "deals": int(tally[category])})
            seen.add(category)
    for category, count in sorted(tally.items()):
        if category not in seen:
            rows.append({"category": category, "deals": int(count)})
    return rows


def build_scrape_report(
    session: Session,
    *,
    discovered: int | None = None,
    ingested: int | None = None,
    marketing_contacts_upserted: int | None = None,
    runtime_seconds: float | None = None,
    markets: list[str] | None = None,
    run_breakdown: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Assemble the /scrape skill result payload.

    Prefer `run_breakdown` (this scrape's deals) when provided; otherwise
    derive country/city/category from active deals in the DB.
    """
    market_list = list(markets or TARGET_MARKETS)
    areas = sum(len(MARKET_CITIES.get(code, [])) for code in market_list)

    unique_contacts = int(
        session.execute(select(func.count()).select_from(MarketingContact)).scalar_one()
    )

    if run_breakdown is not None:
        breakdown_rows = list(run_breakdown)
    else:
        breakdown_rows = _breakdown_from_db(session)

    by_country: dict[str, int] = defaultdict(int)
    category_tally: Counter[str] = Counter()
    for row in breakdown_rows:
        by_country[str(row["country"])] += int(row["deals"])
        category_tally[str(row["category"])] += int(row["deals"])

    active_deals = int(
        session.execute(
            select(func.count()).select_from(Deal).where(Deal.is_active.is_(True))
        ).scalar_one()
    )

    return {
        "summary": {
            "areas": areas,
            "markets": len(market_list),
            "market_codes": market_list,
            "deals_discovered": discovered if discovered is not None else active_deals,
            "deals_ingested": ingested if ingested is not None else active_deals,
            "marketing_contacts_upserted": (
                marketing_contacts_upserted
                if marketing_contacts_upserted is not None
                else unique_contacts
            ),
            "marketing_contacts_unique": unique_contacts,
            "runtime_seconds": runtime_seconds,
            "active_deals_in_db": active_deals,
        },
        "by_country": dict(sorted(by_country.items())),
        "breakdown": breakdown_rows,
        "category_tally": _category_tally_rows(category_tally),
    }


def _breakdown_from_db(session: Session) -> list[dict[str, Any]]:
    contacts = session.execute(select(MarketingContact)).scalars().all()
    contact_lookup: dict[tuple[str, str, str], str] = {}
    for contact in contacts:
        key = (
            contact.country_code.upper(),
            (contact.city or "Unknown").lower(),
            contact.business_name.lower(),
        )
        if contact.venue_category:
            contact_lookup[key] = contact.venue_category

    deals = (
        session.execute(
            select(Deal)
            .where(Deal.is_active.is_(True))
            .options(selectinload(Deal.merchant).selectinload(Merchant.location))
        )
        .scalars()
        .unique()
        .all()
    )

    counter: Counter[tuple[str, str, str]] = Counter()
    for deal in deals:
        merchant = deal.merchant
        location = merchant.location if merchant else None
        country = (location.country_code if location else "??").upper()
        city = location.city if location and location.city else "Unknown"
        name = merchant.name if merchant else ""
        category = contact_lookup.get(
            (country, city.lower(), name.lower()),
            categorize_venue(name),
        )
        counter[(country, city, category)] += 1
    return _rows_from_counter(counter)


def merge_breakdown_rows(
    batches: Iterable[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Sum multiple breakdown batch lists into one."""
    counter: Counter[tuple[str, str, str]] = Counter()
    for batch in batches:
        for row in batch:
            counter[
                (str(row["country"]), str(row["city"]), str(row["category"]))
            ] += int(row["deals"])
    return _rows_from_counter(counter)
