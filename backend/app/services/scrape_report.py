"""Build scrape result reports (summary + country/city/category breakdowns)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.models.deal import Deal
from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant
from app.scrapers.categories import CATEGORY_ORDER, categorize_venue
from app.scrapers.markets import MARKET_CITIES, TARGET_MARKETS


def breakdown_from_scraped_deals(
    deals: Sequence[Any],
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


def contact_category_stmt() -> Select[Any]:
    """Category labels for the contact ledger, without full contact rows."""
    return select(
        MarketingContact.country_code,
        MarketingContact.city,
        MarketingContact.business_name,
        MarketingContact.venue_category,
    ).where(MarketingContact.venue_category.is_not(None))


def active_deal_location_stmt() -> Select[Any]:
    """Active deals as country / city / merchant name only.

    Loading Deal entities also selectin-loads items and translations
    (about 11k deals and their children). The report only needs counts.
    """
    return (
        select(Location.country_code, Location.city, Merchant.name)
        .select_from(Deal)
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .join(Location, Merchant.location_id == Location.id)
        .where(Deal.is_active.is_(True))
    )


def breakdown_from_rows(
    contact_rows: Sequence[tuple[Any, ...]],
    deal_rows: Sequence[tuple[Any, ...]],
) -> list[dict[str, Any]]:
    """Same category rules as the previous ORM walk, on narrow tuples."""
    contact_lookup: dict[tuple[str, str, str], str] = {}
    for country_code, city, business_name, venue_category in contact_rows:
        if not venue_category:
            continue
        key = (
            (country_code or "??").upper(),
            (city or "Unknown").lower(),
            (business_name or "").lower(),
        )
        contact_lookup[key] = str(venue_category)

    counter: Counter[tuple[str, str, str]] = Counter()
    for country_code, city, merchant_name in deal_rows:
        country = (country_code or "??").upper()
        city_name = city if city else "Unknown"
        name = merchant_name or ""
        category = contact_lookup.get(
            (country, city_name.lower(), name.lower()),
            categorize_venue(name),
        )
        counter[(country, city_name, category)] += 1
    return _rows_from_counter(counter)


def _breakdown_from_db(session: Session) -> list[dict[str, Any]]:
    contacts = session.execute(contact_category_stmt()).all()
    deals = session.execute(active_deal_location_stmt()).all()
    return breakdown_from_rows(contacts, deals)


async def _breakdown_from_db_async(session: AsyncSession) -> list[dict[str, Any]]:
    contacts = (await session.execute(contact_category_stmt())).all()
    deals = (await session.execute(active_deal_location_stmt())).all()
    return breakdown_from_rows(contacts, deals)


def _assemble_report(
    *,
    breakdown_rows: list[dict[str, Any]],
    unique_contacts: int,
    active_deals: int,
    discovered: int | None,
    ingested: int | None,
    marketing_contacts_upserted: int | None,
    runtime_seconds: float | None,
    market_list: list[str],
) -> dict[str, Any]:
    areas = sum(len(MARKET_CITIES.get(code, [])) for code in market_list)
    by_country: dict[str, int] = defaultdict(int)
    category_tally: Counter[str] = Counter()
    for row in breakdown_rows:
        by_country[str(row["country"])] += int(row["deals"])
        category_tally[str(row["category"])] += int(row["deals"])

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
    unique_contacts = int(
        session.execute(select(func.count()).select_from(MarketingContact)).scalar_one()
    )
    active_deals = int(
        session.execute(
            select(func.count()).select_from(Deal).where(Deal.is_active.is_(True))
        ).scalar_one()
    )
    breakdown_rows = (
        list(run_breakdown) if run_breakdown is not None else _breakdown_from_db(session)
    )
    return _assemble_report(
        breakdown_rows=breakdown_rows,
        unique_contacts=unique_contacts,
        active_deals=active_deals,
        discovered=discovered,
        ingested=ingested,
        marketing_contacts_upserted=marketing_contacts_upserted,
        runtime_seconds=runtime_seconds,
        market_list=market_list,
    )


async def build_scrape_report_async(
    session: AsyncSession,
    *,
    discovered: int | None = None,
    ingested: int | None = None,
    marketing_contacts_upserted: int | None = None,
    runtime_seconds: float | None = None,
    markets: list[str] | None = None,
    run_breakdown: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Async form of build_scrape_report for the API process."""
    market_list = list(markets or TARGET_MARKETS)
    unique_contacts = int(
        await session.scalar(select(func.count()).select_from(MarketingContact)) or 0
    )
    active_deals = int(
        await session.scalar(
            select(func.count()).select_from(Deal).where(Deal.is_active.is_(True))
        )
        or 0
    )
    breakdown_rows = (
        list(run_breakdown)
        if run_breakdown is not None
        else await _breakdown_from_db_async(session)
    )
    return _assemble_report(
        breakdown_rows=breakdown_rows,
        unique_contacts=unique_contacts,
        active_deals=active_deals,
        discovered=discovered,
        ingested=ingested,
        marketing_contacts_upserted=marketing_contacts_upserted,
        runtime_seconds=runtime_seconds,
        market_list=market_list,
    )


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
