"""Persist scraped deals into locations / merchants / deals tables."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.deal import Deal, DealItem, ItemCategory
from app.models.location import Location
from app.models.merchant import Merchant, MerchantCategory, TierLevel
from app.models.translation import DealTranslation
from app.scrapers.base import ScrapedDeal
from app.scrapers.categories import venue_category_id
from app.scrapers.catchment_hubs import CATCHMENT_COORDS
from app.scrapers.markets import (
    CITY_COORDS as NEW_CITY_COORDS,
    COUNTRY_TIMEZONES as MARKET_COUNTRY_TIMEZONES,
)
from app.services.affiliate import build_affiliate_urls
from app.services.city_coords import STATIC_CITY_COORDS
from app.services.deal_link import check_url_reachable, normalize_outbound_url
from app.services.geo_names import COUNTRY_ALIASES, normalize_city, normalize_country

__all__ = [
    "CITY_COORDS",
    "COUNTRY_ALIASES",
    "normalize_city",
    "normalize_country",
]

logger = logging.getLogger(__name__)

# Rough city centroids for PostGIS points (lat, lon).
# The literal lives in city_coords so API geocoding does not import this module.
CITY_COORDS: dict[tuple[str, str], tuple[float, float]] = dict(STATIC_CITY_COORDS)
CITY_COORDS.update(NEW_CITY_COORDS)
CITY_COORDS.update(CATCHMENT_COORDS)


_COUNTRY_TIMEZONES: dict[str, str] = {
    "GB": "Europe/London",
    "IE": "Europe/Dublin",
    "US": "America/New_York",
    "CA": "America/Toronto",
    "AU": "Australia/Sydney",
    "NZ": "Pacific/Auckland",
    "PH": "Asia/Manila",
    "TH": "Asia/Bangkok",
    "NL": "Europe/Amsterdam",
    "BS": "America/Nassau",
    "JM": "America/Jamaica",
}
_COUNTRY_TIMEZONES.update(MARKET_COUNTRY_TIMEZONES)

CITY_TIMEZONES: dict[tuple[str, str], str] = {
    ("US", "Los Angeles"): "America/Los_Angeles",
    ("US", "San Francisco"): "America/Los_Angeles",
    ("US", "San Diego"): "America/Los_Angeles",
    ("US", "San Jose"): "America/Los_Angeles",
    ("US", "Sacramento"): "America/Los_Angeles",
    ("US", "Seattle"): "America/Los_Angeles",
    ("US", "Portland"): "America/Los_Angeles",
    ("US", "Las Vegas"): "America/Los_Angeles",
    ("US", "Phoenix"): "America/Phoenix",
    ("US", "Denver"): "America/Denver",
    ("US", "Salt Lake City"): "America/Denver",
    ("US", "Chicago"): "America/Chicago",
    ("US", "Houston"): "America/Chicago",
    ("US", "Dallas"): "America/Chicago",
    ("US", "Austin"): "America/Chicago",
    ("US", "San Antonio"): "America/Chicago",
    ("US", "Minneapolis"): "America/Chicago",
    ("US", "Kansas City"): "America/Chicago",
    ("US", "St Louis"): "America/Chicago",
    ("US", "Milwaukee"): "America/Chicago",
    ("US", "Honolulu"): "Pacific/Honolulu",
    ("CA", "Vancouver"): "America/Vancouver",
    ("CA", "Victoria"): "America/Vancouver",
    ("CA", "Surrey"): "America/Vancouver",
    ("CA", "Calgary"): "America/Edmonton",
    ("CA", "Edmonton"): "America/Edmonton",
    ("CA", "Winnipeg"): "America/Winnipeg",
    ("CA", "Regina"): "America/Regina",
    ("CA", "Saskatoon"): "America/Regina",
    ("CA", "Halifax"): "America/Halifax",
    ("AU", "Melbourne"): "Australia/Melbourne",
    ("AU", "Brisbane"): "Australia/Brisbane",
    ("AU", "Perth"): "Australia/Perth",
    ("AU", "Adelaide"): "Australia/Adelaide",
    ("AU", "Hobart"): "Australia/Hobart",
    ("AU", "Darwin"): "Australia/Darwin",
    ("NZ", "Wellington"): "Pacific/Auckland",
    ("NZ", "Christchurch"): "Pacific/Auckland",
}


def _coords_for(country: str, city: str) -> tuple[float, float]:
    key = (country, city)
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    # Fallback: slight hash offset so cities don't collide at 0,0
    seed = abs(hash(f"{country}:{city}")) % 1000
    return (20.0 + (seed % 50), -10.0 + (seed % 40))


def get_or_create_location(
    session: Session,
    country_code: str,
    city: str,
    *,
    area_local: str | None = None,
) -> Location:
    country = normalize_country(country_code)
    city_name = normalize_city(city)
    locality = (area_local or "").strip() or None
    # Prefer the canonical hub + locality; tolerate duplicate rows from earlier scrapes.
    stmt = select(Location).where(
        Location.country_code == country,
        Location.city.ilike(city_name),
    )
    if locality:
        stmt = stmt.where(Location.area_local.ilike(locality))
    else:
        stmt = stmt.where(Location.area_local.is_(None))
    existing = session.execute(
        stmt.order_by(Location.city.asc(), Location.id.asc()).limit(1)
    ).scalar_one_or_none()
    if existing:
        return existing

    lat, lon = _coords_for(country, city_name)
    location = Location(
        id=uuid.uuid4(),
        country_code=country,
        city=city_name,
        area_local=locality,
        timezone=CITY_TIMEZONES.get(
            (country, city_name), _COUNTRY_TIMEZONES.get(country, "UTC")
        ),
        latitude=lat,
        longitude=lon,
        geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
    )
    session.add(location)
    session.flush()
    return location


def _apply_scraped_merchant_profile(merchant: Merchant, scraped: ScrapedDeal) -> None:
    """Refresh logo / website / about blurb from scrape without wiping other fields."""
    if scraped.logo_url:
        merchant.logo_url = scraped.logo_url[:500]
    if scraped.website:
        merchant.website = scraped.website[:500]
    if scraped.about_blurb:
        merchant.bio = scraped.about_blurb[:2000]


def get_or_create_scraped_merchant(
    session: Session,
    *,
    name: str,
    location: Location,
    scraped: ScrapedDeal | None = None,
) -> Merchant:
    existing = session.execute(
        select(Merchant).where(
            Merchant.name == name,
            Merchant.location_id == location.id,
        )
    ).scalar_one_or_none()
    if existing:
        if scraped is not None:
            _apply_scraped_merchant_profile(existing, scraped)
        return existing

    merchant = Merchant(
        id=uuid.uuid4(),
        name=name,
        category=MerchantCategory.SUPERMARKET,
        location_id=location.id,
        is_subscriber=False,
        tier_level=TierLevel.FREE,
        deal_slot_limit=0,
        subscription_phase="none",
        website=scraped.website[:500] if scraped and scraped.website else None,
        logo_url=scraped.logo_url[:500] if scraped and scraped.logo_url else None,
        bio=scraped.about_blurb[:2000] if scraped and scraped.about_blurb else None,
    )
    session.add(merchant)
    session.flush()
    return merchant


def _scraped_deal_expires_at() -> datetime:
    days = get_settings().scraped_deal_ttl_days
    return datetime.now(timezone.utc) + timedelta(days=days)


def _seen_clean_urls(scraped_deals: Sequence[ScrapedDeal]) -> set[str]:
    seen: set[str] = set()
    for scraped in scraped_deals:
        clean_url, _ = build_affiliate_urls(scraped.raw_url)
        if clean_url:
            seen.add(clean_url)
    return seen


def deactivate_stale_scraped_deals_for_hub(
    session: Session,
    country_code: str,
    hub_city: str,
    scraped_deals: Sequence[ScrapedDeal],
) -> int:
    """
    Drop scraped deals under a hub that were not seen in the latest hub pass.

    Subscriber-posted deals are never touched.
    """
    country = normalize_country(country_code)
    hub = normalize_city(hub_city)
    seen = _seen_clean_urls(scraped_deals)
    now = datetime.now(timezone.utc)

    stmt = (
        select(Deal)
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .join(Location, Merchant.location_id == Location.id)
        .where(Merchant.is_subscriber.is_(False))
        .where(Deal.scraped_raw_url.isnot(None))
        .where(Deal.is_active.is_(True))
        .where(Location.country_code == country)
        .where(Location.city.ilike(hub))
    )
    deactivated = 0
    for deal in session.scalars(stmt).all():
        if deal.clean_url and deal.clean_url in seen:
            continue
        deal.is_active = False
        deal.expires_at = now
        deactivated += 1

    if deactivated:
        logger.info(
            "Deactivated %d stale scraped deals for %s/%s",
            deactivated,
            country,
            hub,
        )
    return deactivated


def _item_category(raw: str) -> ItemCategory:
    try:
        return ItemCategory(raw.lower())
    except ValueError:
        return ItemCategory.MAIN


def _refresh_deal_translation(
    session: Session, deal: Deal, scraped: ScrapedDeal
) -> None:
    lang = scraped.language_code or "en"
    existing_tr = next(
        (t for t in (deal.translations or []) if t.language_code == lang),
        None,
    )
    if existing_tr:
        existing_tr.title = scraped.title[:255]
        existing_tr.description = scraped.description
        return
    session.add(
        DealTranslation(
            deal_id=deal.id,
            language_code=lang,
            title=scraped.title[:255],
            description=scraped.description,
        )
    )


def _refresh_deal_items(session: Session, deal: Deal, scraped: ScrapedDeal) -> None:
    if not scraped.items:
        return
    for item in list(deal.items or []):
        session.delete(item)
    for item in scraped.items:
        session.add(
            DealItem(
                id=uuid.uuid4(),
                deal_id=deal.id,
                category=_item_category(str(item.get("category", "main"))),
                item_name=str(item.get("item_name", "Item"))[:255],
                individual_price=Decimal(str(item.get("individual_price", "0"))),
            )
        )


def upsert_scraped_deal(session: Session, scraped: ScrapedDeal) -> Deal | None:
    """Insert or refresh a scraped deal (matched on clean_url)."""
    clean_url, affiliate_url = build_affiliate_urls(scraped.raw_url)

    existing = None
    if clean_url:
        existing = session.execute(
            select(Deal)
            .where(Deal.clean_url == clean_url)
            .options(selectinload(Deal.items), selectinload(Deal.translations))
            .limit(1)
        ).scalar_one_or_none()

    outbound = normalize_outbound_url(affiliate_url or clean_url or scraped.raw_url)
    if not outbound or not check_url_reachable(outbound):
        logger.info(
            "Skipping scraped deal (unreachable URL): %s → %s",
            scraped.merchant_name,
            outbound or scraped.raw_url,
        )
        if existing is not None:
            existing.is_active = False
            session.flush()
        return None

    if existing:
        existing.original_price = scraped.original_price
        existing.deal_price = scraped.deal_price
        existing.currency_code = scraped.currency_code.upper()
        existing.affiliate_url = affiliate_url
        existing.scraped_raw_url = scraped.raw_url
        existing.is_active = True
        existing.expires_at = _scraped_deal_expires_at()
        if scraped.image_url:
            existing.image_url = scraped.image_url[:500]
        existing.venue_category = venue_category_id(
            scraped.venue_category, merchant_name=scraped.merchant_name
        )
        merchant = session.get(Merchant, existing.merchant_id)
        if merchant is not None:
            _apply_scraped_merchant_profile(merchant, scraped)
            # Refresh nested locality when hub/town labels improve on re-scrape.
            country = normalize_country(scraped.country_code)
            hub = normalize_city(scraped.area_hub or scraped.city)
            locality = (scraped.area_local or "").strip() or None
            location = get_or_create_location(
                session, country, hub, area_local=locality
            )
            if merchant.location_id != location.id:
                merchant.location_id = location.id
        _refresh_deal_translation(session, existing, scraped)
        _refresh_deal_items(session, existing, scraped)
        session.flush()
        return existing

    country = normalize_country(scraped.country_code)
    hub = normalize_city(scraped.area_hub or scraped.city)
    locality = (scraped.area_local or "").strip() or None
    location = get_or_create_location(session, country, hub, area_local=locality)
    merchant = get_or_create_scraped_merchant(
        session,
        name=scraped.merchant_name,
        location=location,
        scraped=scraped,
    )

    deal = Deal(
        id=uuid.uuid4(),
        merchant_id=merchant.id,
        scraped_raw_url=scraped.raw_url,
        clean_url=clean_url,
        affiliate_url=affiliate_url,
        original_price=scraped.original_price,
        deal_price=scraped.deal_price,
        currency_code=scraped.currency_code.upper(),
        image_url=scraped.image_url[:500] if scraped.image_url else None,
        venue_category=venue_category_id(
            scraped.venue_category, merchant_name=scraped.merchant_name
        ),
        is_active=True,
        expires_at=_scraped_deal_expires_at(),
        tier_priority_score=0,
    )
    session.add(deal)
    session.flush()

    for item in scraped.items:
        session.add(
            DealItem(
                id=uuid.uuid4(),
                deal_id=deal.id,
                category=_item_category(str(item.get("category", "main"))),
                item_name=str(item.get("item_name", "Item"))[:255],
                individual_price=Decimal(str(item.get("individual_price", "0"))),
            )
        )

    session.add(
        DealTranslation(
            deal_id=deal.id,
            language_code=scraped.language_code or "en",
            title=scraped.title[:255],
            description=scraped.description,
        )
    )

    session.flush()
    return deal


def ingest_scraped_deals(session: Session, deals: Sequence[ScrapedDeal]) -> int:
    count = 0
    for scraped in deals:
        try:
            if upsert_scraped_deal(session, scraped) is None:
                continue
            count += 1
        except Exception:
            logger.exception(
                "Failed to ingest scraped deal from %s", scraped.merchant_name
            )
    session.commit()
    logger.info("Ingested %d scraped deals", count)
    return count


def ingest_hub_scrape(
    session: Session,
    country_code: str,
    hub_city: str,
    deals: Sequence[ScrapedDeal],
) -> dict[str, int]:
    """Ingest one hub pass, drop stale scraped deals for that hub, commit."""
    ingested = 0
    for scraped in deals:
        try:
            if upsert_scraped_deal(session, scraped) is None:
                continue
            ingested += 1
        except Exception:
            logger.exception(
                "Failed to ingest scraped deal from %s", scraped.merchant_name
            )
    stale = deactivate_stale_scraped_deals_for_hub(
        session, country_code, hub_city, deals
    )
    session.commit()
    logger.info(
        "Hub %s/%s: ingested=%d stale_deactivated=%d",
        normalize_country(country_code),
        normalize_city(hub_city),
        ingested,
        stale,
    )
    return {"ingested": ingested, "stale_deactivated": stale}
