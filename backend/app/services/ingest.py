"""Persist scraped deals into locations / merchants / deals tables."""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.deal import Deal, DealItem, ItemCategory
from app.models.location import Location
from app.models.merchant import Merchant, MerchantCategory, TierLevel
from app.models.translation import DealTranslation
from app.scrapers.base import ScrapedDeal
from app.scrapers.categories import venue_category_id
from app.scrapers.markets import (
    CITY_COORDS as NEW_CITY_COORDS,
    COUNTRY_TIMEZONES as MARKET_COUNTRY_TIMEZONES,
)
from app.services.affiliate import build_affiliate_urls

logger = logging.getLogger(__name__)

# Rough city centroids for PostGIS points (lat, lon)
CITY_COORDS: dict[tuple[str, str], tuple[float, float]] = {
    # United Kingdom
    ("GB", "London"): (51.5074, -0.1278),
    ("GB", "Manchester"): (53.4808, -2.2426),
    ("GB", "Birmingham"): (52.4862, -1.8904),
    ("GB", "Leeds"): (53.8008, -1.5491),
    ("GB", "Glasgow"): (55.8642, -4.2518),
    ("GB", "Edinburgh"): (55.9533, -3.1883),
    ("GB", "Liverpool"): (53.4084, -2.9916),
    ("GB", "Bristol"): (51.4545, -2.5879),
    ("GB", "Sheffield"): (53.3811, -1.4701),
    ("GB", "Newcastle"): (54.9783, -1.6178),
    ("GB", "Cardiff"): (51.4816, -3.1791),
    ("GB", "Belfast"): (54.5973, -5.9301),
    ("GB", "Nottingham"): (52.9548, -1.1581),
    ("GB", "Leicester"): (52.6369, -1.1398),
    ("GB", "Brighton"): (50.8225, -0.1372),
    ("GB", "Southampton"): (50.9097, -1.4044),
    ("GB", "Coventry"): (52.4068, -1.5197),
    ("GB", "Reading"): (51.4543, -0.9781),
    ("GB", "Cambridge"): (52.2053, 0.1218),
    ("GB", "Oxford"): (51.7520, -1.2577),
    ("GB", "Aberdeen"): (57.1497, -2.0943),
    ("GB", "Plymouth"): (50.3755, -4.1427),
    ("GB", "Swansea"): (51.6214, -3.9436),
    ("GB", "York"): (53.9600, -1.0873),
    ("GB", "Bath"): (51.3811, -2.3590),
    # United States
    ("US", "New York"): (40.7128, -74.0060),
    ("US", "Los Angeles"): (34.0522, -118.2437),
    ("US", "Chicago"): (41.8781, -87.6298),
    ("US", "Houston"): (29.7604, -95.3698),
    ("US", "Phoenix"): (33.4484, -112.0740),
    ("US", "Philadelphia"): (39.9526, -75.1652),
    ("US", "San Antonio"): (29.4241, -98.4936),
    ("US", "San Diego"): (32.7157, -117.1611),
    ("US", "Dallas"): (32.7767, -96.7970),
    ("US", "San Jose"): (37.3382, -121.8863),
    ("US", "Austin"): (30.2672, -97.7431),
    ("US", "Jacksonville"): (30.3322, -81.6557),
    ("US", "San Francisco"): (37.7749, -122.4194),
    ("US", "Seattle"): (47.6062, -122.3321),
    ("US", "Denver"): (39.7392, -104.9903),
    ("US", "Boston"): (42.3601, -71.0589),
    ("US", "Nashville"): (36.1627, -86.7816),
    ("US", "Detroit"): (42.3314, -83.0458),
    ("US", "Portland"): (45.5152, -122.6784),
    ("US", "Las Vegas"): (36.1699, -115.1398),
    ("US", "Miami"): (25.7617, -80.1918),
    ("US", "Atlanta"): (33.7490, -84.3880),
    ("US", "Washington"): (38.9072, -77.0369),
    ("US", "Minneapolis"): (44.9778, -93.2650),
    ("US", "Charlotte"): (35.2271, -80.8431),
    ("US", "Tampa"): (27.9506, -82.4572),
    ("US", "Orlando"): (28.5383, -81.3792),
    ("US", "Cleveland"): (41.4993, -81.6944),
    ("US", "Pittsburgh"): (40.4406, -79.9959),
    ("US", "Kansas City"): (39.0997, -94.5786),
    ("US", "St Louis"): (38.6270, -90.1994),
    ("US", "Sacramento"): (38.5816, -121.4944),
    ("US", "Salt Lake City"): (40.7608, -111.8910),
    ("US", "Honolulu"): (21.3069, -157.8583),
    ("US", "New Orleans"): (29.9511, -90.0715),
    ("US", "Raleigh"): (35.7796, -78.6382),
    ("US", "Columbus"): (39.9612, -82.9988),
    ("US", "Indianapolis"): (39.7684, -86.1581),
    ("US", "Cincinnati"): (39.1031, -84.5120),
    ("US", "Milwaukee"): (43.0389, -87.9065),
    # Canada
    ("CA", "Toronto"): (43.6532, -79.3832),
    ("CA", "Vancouver"): (49.2827, -123.1207),
    ("CA", "Montreal"): (45.5017, -73.5673),
    ("CA", "Calgary"): (51.0447, -114.0719),
    ("CA", "Ottawa"): (45.4215, -75.6972),
    ("CA", "Edmonton"): (53.5461, -113.4938),
    ("CA", "Winnipeg"): (49.8951, -97.1384),
    ("CA", "Quebec City"): (46.8139, -71.2080),
    ("CA", "Hamilton"): (43.2557, -79.8711),
    ("CA", "Halifax"): (44.6488, -63.5752),
    ("CA", "Victoria"): (48.4284, -123.3656),
    ("CA", "Saskatoon"): (52.1332, -106.6700),
    ("CA", "Regina"): (50.4452, -104.6189),
    ("CA", "London"): (42.9849, -81.2453),
    ("CA", "Kitchener"): (43.4516, -80.4925),
    ("CA", "Mississauga"): (43.5890, -79.6441),
    ("CA", "Brampton"): (43.7315, -79.7624),
    ("CA", "Surrey"): (49.1913, -122.8490),
    # Ireland
    ("IE", "Dublin"): (53.3498, -6.2603),
    ("IE", "Cork"): (51.8985, -8.4756),
    ("IE", "Galway"): (53.2707, -9.0568),
    ("IE", "Limerick"): (52.6638, -8.6267),
    ("IE", "Waterford"): (52.2593, -7.1101),
    ("IE", "Kilkenny"): (52.6541, -7.2448),
    ("IE", "Sligo"): (54.2766, -8.4761),
    ("IE", "Drogheda"): (53.7179, -6.3561),
    ("IE", "Dundalk"): (54.0043, -6.4129),
    ("IE", "Wexford"): (52.3369, -6.4633),
    # Australia
    ("AU", "Sydney"): (-33.8688, 151.2093),
    ("AU", "Melbourne"): (-37.8136, 144.9631),
    ("AU", "Brisbane"): (-27.4698, 153.0251),
    ("AU", "Perth"): (-31.9505, 115.8605),
    ("AU", "Adelaide"): (-34.9285, 138.6007),
    ("AU", "Canberra"): (-35.2809, 149.1300),
    ("AU", "Hobart"): (-42.8821, 147.3272),
    ("AU", "Gold Coast"): (-28.0167, 153.4000),
    ("AU", "Newcastle"): (-32.9283, 151.7817),
    ("AU", "Wollongong"): (-34.4278, 150.8931),
    ("AU", "Geelong"): (-38.1499, 144.3617),
    ("AU", "Cairns"): (-16.9186, 145.7781),
    ("AU", "Darwin"): (-12.4634, 130.8456),
    ("AU", "Townsville"): (-19.2590, 146.8169),
    ("AU", "Sunshine Coast"): (-26.6500, 153.0667),
    # New Zealand
    ("NZ", "Auckland"): (-36.8485, 174.7633),
    ("NZ", "Wellington"): (-41.2865, 174.7762),
    ("NZ", "Christchurch"): (-43.5321, 172.6362),
    ("NZ", "Hamilton"): (-37.7870, 175.2793),
    ("NZ", "Tauranga"): (-37.6878, 176.1651),
    ("NZ", "Dunedin"): (-45.8788, 170.5028),
    ("NZ", "Queenstown"): (-45.0312, 168.6626),
    ("NZ", "Palmerston North"): (-40.3523, 175.6082),
    ("NZ", "Napier"): (-39.4928, 176.9120),
    ("NZ", "Nelson"): (-41.2706, 173.2840),
    # Philippines
    ("PH", "Manila"): (14.5995, 120.9842),
    ("PH", "Quezon City"): (14.6760, 121.0437),
    ("PH", "Cebu"): (10.3157, 123.8854),
    ("PH", "Davao"): (7.1907, 125.4553),
    ("PH", "Makati"): (14.5547, 121.0244),
    ("PH", "Pasig"): (14.5764, 121.0851),
    ("PH", "Taguig"): (14.5176, 121.0509),
    ("PH", "Iloilo"): (10.7202, 122.5621),
    ("PH", "Cagayan De Oro"): (8.4542, 124.6319),
    ("PH", "Bacolod"): (10.6765, 122.9509),
    ("PH", "Baguio"): (16.4023, 120.5960),
    ("PH", "Angeles"): (15.1449, 120.5887),
    # Thailand
    ("TH", "Bangkok"): (13.7563, 100.5018),
    ("TH", "Chiang Mai"): (18.7883, 98.9853),
    ("TH", "Phuket"): (7.8804, 98.3923),
    ("TH", "Pattaya"): (12.9236, 100.8825),
    ("TH", "Chiang Rai"): (19.9105, 99.8406),
    ("TH", "Hat Yai"): (7.0086, 100.4767),
    ("TH", "Khon Kaen"): (16.4322, 102.8236),
    ("TH", "Hua Hin"): (12.5684, 99.9577),
    ("TH", "Krabi"): (8.0863, 98.9063),
    ("TH", "Udon Thani"): (17.4156, 102.7872),
    # Netherlands
    ("NL", "Amsterdam"): (52.3676, 4.9041),
    ("NL", "Rotterdam"): (51.9244, 4.4777),
    ("NL", "The Hague"): (52.0705, 4.3007),
    ("NL", "Utrecht"): (52.0907, 5.1214),
    ("NL", "Eindhoven"): (51.4416, 5.4697),
    ("NL", "Groningen"): (53.2194, 6.5665),
    ("NL", "Maastricht"): (50.8514, 5.6909),
    ("NL", "Haarlem"): (52.3874, 4.6462),
    ("NL", "Tilburg"): (51.5555, 5.0913),
    ("NL", "Leiden"): (52.1601, 4.4970),
    # Bahamas
    ("BS", "Nassau"): (25.0443, -77.3504),
    ("BS", "Freeport"): (26.5333, -78.7000),
    ("BS", "Marsh Harbour"): (26.5412, -77.0636),
    # Jamaica
    ("JM", "Kingston"): (17.9714, -76.7931),
    ("JM", "Montego Bay"): (18.4762, -77.8939),
    ("JM", "Ocho Rios"): (18.4074, -77.1031),
    ("JM", "Spanish Town"): (17.9911, -76.9574),
    ("JM", "Negril"): (18.2686, -78.3480),
}
CITY_COORDS.update(NEW_CITY_COORDS)

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

COUNTRY_ALIASES: dict[str, str] = {
    "UK": "GB",
    "EI": "IE",
    "UAE": "AE",
}


def normalize_country(code: str) -> str:
    upper = code.strip().upper()
    return COUNTRY_ALIASES.get(upper, upper)


def normalize_city(city: str) -> str:
    return " ".join(part.capitalize() for part in city.replace("-", " ").split())


def _coords_for(country: str, city: str) -> tuple[float, float]:
    key = (country, city)
    if key in CITY_COORDS:
        return CITY_COORDS[key]
    # Fallback: slight hash offset so cities don't collide at 0,0
    seed = abs(hash(f"{country}:{city}")) % 1000
    return (20.0 + (seed % 50), -10.0 + (seed % 40))


def get_or_create_location(session: Session, country_code: str, city: str) -> Location:
    country = normalize_country(country_code)
    city_name = normalize_city(city)
    # Prefer the canonical city name; tolerate duplicate rows from earlier scrapes.
    existing = session.execute(
        select(Location)
        .where(
            Location.country_code == country,
            Location.city.ilike(city_name),
        )
        .order_by(Location.city.asc(), Location.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    if existing:
        return existing

    lat, lon = _coords_for(country, city_name)
    location = Location(
        id=uuid.uuid4(),
        country_code=country,
        city=city_name,
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


def _item_category(raw: str) -> ItemCategory:
    try:
        return ItemCategory(raw.lower())
    except ValueError:
        return ItemCategory.MAIN


def upsert_scraped_deal(session: Session, scraped: ScrapedDeal) -> Deal:
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

    if existing:
        existing.original_price = scraped.original_price
        existing.deal_price = scraped.deal_price
        existing.currency_code = scraped.currency_code.upper()
        existing.affiliate_url = affiliate_url
        existing.scraped_raw_url = scraped.raw_url
        existing.is_active = True
        if scraped.image_url:
            existing.image_url = scraped.image_url[:500]
        existing.venue_category = venue_category_id(
            scraped.venue_category, merchant_name=scraped.merchant_name
        )
        merchant = session.get(Merchant, existing.merchant_id)
        if merchant is not None:
            _apply_scraped_merchant_profile(merchant, scraped)
        session.flush()
        return existing

    country = normalize_country(scraped.country_code)
    city = normalize_city(scraped.city)
    location = get_or_create_location(session, country, city)
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
            upsert_scraped_deal(session, scraped)
            count += 1
        except Exception:
            logger.exception(
                "Failed to ingest scraped deal from %s", scraped.merchant_name
            )
    session.commit()
    logger.info("Ingested %d scraped deals", count)
    return count
