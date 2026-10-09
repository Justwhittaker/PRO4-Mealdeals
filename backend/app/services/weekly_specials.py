"""Friday Weekly Specials: local deals only, quality-filtered, on-site links.

Location fallback
-----------------
The subscriber's stored ``country_code`` and ``city`` are used when both
are set. Otherwise the free-text ``location`` field is parsed ("Galway",
"Galway, Ireland"). A city name that exists in exactly one country is
enough. A city that exists in several countries (London) is used only
when the country is stored or written in the location text. An unresolved
place does not receive deals from anywhere else.

Eligible deals are then taken in this order, and only from that country:

1. The subscriber's city (a "Galway City" label matches Galway).
2. Other cities in the same country within ``NEARBY_RADIUS_KM`` (120) of
   the subscriber city centroid, nearest first. Distance uses the venue
   coordinates when they exist, otherwise the city centroid. A nearby
   city across a state line stays in this tier.
3. For the US, Canada, and Australia, the rest of the subscriber's state
   or province (Salt Lake City, then nearby Utah towns, then St. George,
   and not Denver). The state is the city's entry in
   ``app.services.regions``, or the stored ``region`` when the city is
   not in that map.
4. The rest of that country, nearest first. This country tier is used
   only when the state or province has no deal that survives the quality
   filter. A Utah subscriber is not padded with the rest of the US while
   any Utah deal remains. Ireland and other countries without a state
   map skip step 3 and go from nearby towns to the country.

``WEEKLY_CANDIDATE_CAP`` bounds the database read (newest active deals in
the country, plus an extra city query so older hometown deals are not
crowded out). ``WEEKLY_DEAL_LIMIT`` is the maximum number of rows in the
email. A short list is sent as-is. When nothing in the country survives
the quality filter, the email is the "no new local deals this week"
variant. Deals from other countries are not added.

Signup stores country, city, and region. The form prefills from the
site location cookie (IP city and state headers, or the homepage
browser geolocation). Those structured fields are sent while the
subscriber leaves the prefill in place. A known city sets the state
from the city map. Existing rows with a null country, city, or region
are filled from the free-text location on the next successful send
(``backfill_subscriber_location``). A value that is already stored is
left as it is. The email still prefers the city map over a stale
region code when the city is known.

Links
-----
Each row links to the public Dine A Deal deal page with
``utm_source=newsletter&utm_medium=email&utm_campaign=weekly_specials``.
The merchant site is not used in the email. The deal page "View deal"
button continues through ``/go/{deal_id}``; those UTM tags are forwarded
and stored on ``click_events`` so referrals can be counted.

Prices
------
Amounts are converted into the subscriber country's currency
(Ireland → EUR) with the seeded ``CURRENCY_RATES`` table and formatted
with that currency's symbol. A percent-off or free-item offer with no
positive price is shown as that offer, not as 0.00.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from urllib.parse import quote, urlencode

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.deal import Deal
from app.models.location import Location
from app.models.merchant import Merchant
from app.models.newsletter import NewsletterSubscriber
from app.scrapers.markets import CURRENCY_RATES, DEFAULT_CURRENCY
from app.services.city_coords import merged_city_coords
from app.services.deal_quality import (
    filter_kept_in_order,
    promotional_price_label,
    rejection_reason,
)
from app.services.email import send_email
from app.services.frontend_revalidate import frontend_country_slug, slugify_city
from app.services.geo_names import normalize_country
from app.services.regions import (
    region_belongs,
    region_for_city,
    region_from_name,
    region_label,
    regions_with_code,
)

logger = logging.getLogger(__name__)

# Same-country cities at or inside this radius are the "nearby" tier.
NEARBY_RADIUS_KM = 120.0
WEEKLY_DEAL_LIMIT = 12
# Newest active deals loaded per country, so one city cannot be buried
# under a global feed. Exact city matches are queried again on top.
WEEKLY_CANDIDATE_CAP = 400
CITY_MATCH_CAP = 80

_ZERO_DECIMAL = frozenset(
    {"JPY", "KRW", "VND", "CLP", "ISK", "XAF", "XOF", "UGX", "RWF", "VUV"}
)

_COUNTRY_LABELS: dict[str, str] = {
    "AE": "the UAE",
    "AU": "Australia",
    "CA": "Canada",
    "DE": "Germany",
    "ES": "Spain",
    "FJ": "Fiji",
    "FR": "France",
    "GB": "the UK",
    "GY": "Guyana",
    "IE": "Ireland",
    "IT": "Italy",
    "JP": "Japan",
    "KR": "Korea",
    "NL": "the Netherlands",
    "NZ": "New Zealand",
    "PL": "Poland",
    "PT": "Portugal",
    "QA": "Qatar",
    "US": "the US",
    "ZA": "South Africa",
}

_COUNTRY_NAMES: dict[str, str] = {
    "ireland": "IE",
    "eire": "IE",
    "republic of ireland": "IE",
    "uk": "GB",
    "u k": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "america": "US",
    "australia": "AU",
    "new zealand": "NZ",
    "south africa": "ZA",
    "uae": "AE",
    "united arab emirates": "AE",
    "korea": "KR",
    "south korea": "KR",
    "poland": "PL",
    "qatar": "QA",
    "fiji": "FJ",
    "guyana": "GY",
    "canada": "CA",
    "france": "FR",
    "germany": "DE",
    "spain": "ES",
    "italy": "IT",
    "portugal": "PT",
    "netherlands": "NL",
    "the netherlands": "NL",
    "japan": "JP",
}

_UTM = (
    ("utm_source", "newsletter"),
    ("utm_medium", "email"),
    ("utm_campaign", "weekly_specials"),
)


@dataclass(frozen=True)
class WeeklyDeal:
    """One candidate row. ``outbound_url`` is never placed in the email."""

    id: str
    title: str
    description: str
    merchant_name: str
    venue_category: str | None
    country_code: str
    city: str
    latitude: float | None
    longitude: float | None
    deal_price: Decimal | None
    currency_code: str | None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    outbound_url: str | None = None


@dataclass(frozen=True)
class SubscriberPlace:
    country_code: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    city_label: str | None
    country_label: str
    region_code: str | None = None
    region_label: str | None = None

    @property
    def place_label(self) -> str:
        return self.city_label or self.region_label or self.country_label


@dataclass(frozen=True)
class WeeklySelection:
    deals: list[WeeklyDeal]
    scope: str
    city_label: str | None
    country_label: str
    local_currency: str
    region_label: str | None = None

    @property
    def place_label(self) -> str:
        return self.city_label or self.country_label


def _country_label(code: str | None) -> str:
    if not code:
        return "your country"
    return _COUNTRY_LABELS.get(code.upper(), "your country")


def _city_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def same_city(left: str | None, right: str | None) -> bool:
    """True when two labels are the same city, including a trailing "City"."""
    a = _city_key(left)
    b = _city_key(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return a == f"{b}city" or b == f"{a}city"


@lru_cache(maxsize=1)
def _city_index() -> dict[str, list[tuple[str, str, float, float]]]:
    index: dict[str, list[tuple[str, str, float, float]]] = {}
    seen: set[tuple[str, str]] = set()
    for (country, city), (lat, lon) in merged_city_coords().items():
        code = country.upper()
        key = _city_key(city)
        ident = (code, key)
        if not key or ident in seen:
            continue
        seen.add(ident)
        index.setdefault(key, []).append((code, city, float(lat), float(lon)))
    return index


def _cities_named(city: str) -> list[tuple[str, str, float, float]]:
    return list(_city_index().get(_city_key(city), []))


def _centroid(country: str, city: str) -> tuple[float | None, float | None]:
    matches = [row for row in _cities_named(city) if row[0] == country.upper()]
    if len(matches) != 1:
        return None, None
    return matches[0][2], matches[0][3]


def _norm_spaces(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _country_code_from_compact(compact: str) -> str | None:
    """A 2-letter country we publish, including UK → GB. Not a state code."""
    if len(compact) != 2:
        return None
    code = normalize_country(compact)
    if code in DEFAULT_CURRENCY or code in _COUNTRY_LABELS:
        return code
    return None


def _interpret_place_code(
    compact: str,
    city: str | None,
    known_country: str | None,
) -> tuple[str | None, str | None]:
    """Return (country, region) for a 2- or 3-letter token.

    ``CA`` is California when the city is in the US (Los Angeles, CA) and
    Canada when the city is in Canada (Vancouver, CA) or the token stands
    alone. ``UT`` is Utah. ``IE`` stays Ireland.
    """
    region_hits = regions_with_code(compact)
    as_country = _country_code_from_compact(compact)
    if known_country:
        for region_country, _label in region_hits:
            if region_country == known_country:
                return known_country, compact
        return known_country, None

    city_countries = {row[0] for row in _cities_named(city)} if city else set()
    for region_country, _label in region_hits:
        if region_country in city_countries:
            return region_country, compact
    if len(city_countries) == 1:
        only = next(iter(city_countries))
        if as_country is None or as_country == only:
            return only, None
    if as_country and (not city_countries or as_country in city_countries):
        return as_country, None
    if len(region_hits) == 1 and as_country is None:
        return region_hits[0][0], compact
    return None, None


def _parse_location(
    location: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Return (country, city, region code) from free text."""
    text = (location or "").strip()
    if not text:
        return None, None, None
    parts = [part.strip() for part in re.split(r"[,|/]", text) if part.strip()]
    if not parts:
        return None, None, None
    country: str | None = None
    region: str | None = None
    city_parts: list[str] = []
    codes: list[str] = []
    for part in parts:
        spaced = _norm_spaces(part)
        if spaced in _COUNTRY_NAMES:
            if country is None:
                country = _COUNTRY_NAMES[spaced]
            continue
        compact = re.sub(r"[^A-Za-z]", "", part).upper()
        is_short_code = len(compact) == 2 or (
            len(compact) == 3 and bool(regions_with_code(compact))
        )
        if is_short_code and _norm_spaces(part) == compact.lower():
            codes.append(compact)
            continue
        named = region_from_name(spaced)
        if named and not _cities_named(part):
            region_country, region_code = named
            if country is None:
                country = region_country
            if country == region_country and region is None:
                region = region_code
            continue
        city_parts.append(part)
    city = city_parts[0] if city_parts else None
    for compact in codes:
        code_country, code_region = _interpret_place_code(compact, city, country)
        if code_country and country is None:
            country = code_country
        if code_region and region is None and (
            country is None or region_belongs(country, code_region)
        ):
            region = code_region
            if country is None:
                country = code_country
    return country, city, region


def _one_line(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _resolved_region(
    country: str | None,
    city: str | None,
    hinted_region: str | None,
) -> tuple[str | None, str | None]:
    """City map wins. A stored or typed region covers towns missing from the map."""
    mapped = region_for_city(country, city) if country and city else None
    if mapped:
        return mapped
    if hinted_region and region_belongs(country, hinted_region):
        return hinted_region, region_label(country, hinted_region)
    return None, None


def _place(
    *,
    country_code: str | None,
    city: str | None,
    latitude: float | None,
    longitude: float | None,
    city_label: str | None,
    country_label: str,
    hinted_region: str | None,
) -> SubscriberPlace:
    region_code, label = _resolved_region(country_code, city, hinted_region)
    return SubscriberPlace(
        country_code=country_code,
        city=city,
        latitude=latitude,
        longitude=longitude,
        city_label=city_label,
        country_label=country_label,
        region_code=region_code,
        region_label=label,
    )


def resolve_subscriber_place(
    country_code: str | None,
    city: str | None,
    location: str | None,
    region: str | None = None,
) -> SubscriberPlace:
    """Resolve city, state, and country. Never guesses across countries."""
    stored_country = (
        normalize_country(country_code) if (country_code or "").strip() else None
    )
    stored_city = (city or "").strip() or None
    stored_region = re.sub(r"[^A-Za-z0-9]", "", region or "").upper() or None
    hinted_country, hinted_city, hinted_region = _parse_location(location)
    country = stored_country or hinted_country
    city_text = stored_city or hinted_city
    region_hint = stored_region or hinted_region

    if city_text and country is None:
        matches = _cities_named(city_text)
        countries = {row[0] for row in matches}
        if len(countries) == 1 and matches:
            code, canonical, lat, lon = matches[0]
            return _place(
                country_code=code,
                city=canonical,
                latitude=lat,
                longitude=lon,
                city_label=canonical,
                country_label=_country_label(code),
                hinted_region=region_hint,
            )
        label = _one_line(city_text)
        return _place(
            country_code=None,
            city=None,
            latitude=None,
            longitude=None,
            city_label=label or None,
            country_label="your country",
            hinted_region=None,
        )

    if country and city_text:
        matches = [row for row in _cities_named(city_text) if row[0] == country]
        if matches:
            _code, canonical, lat, lon = matches[0]
            return _place(
                country_code=country,
                city=canonical,
                latitude=lat,
                longitude=lon,
                city_label=canonical,
                country_label=_country_label(country),
                hinted_region=region_hint,
            )
        lat, lon = _centroid(country, city_text)
        label = _one_line(city_text)
        return _place(
            country_code=country,
            city=label,
            latitude=lat,
            longitude=lon,
            city_label=label,
            country_label=_country_label(country),
            hinted_region=region_hint,
        )

    if country:
        return _place(
            country_code=country,
            city=None,
            latitude=None,
            longitude=None,
            city_label=None,
            country_label=_country_label(country),
            hinted_region=region_hint,
        )

    fallback = _one_line((location or "").split(",")[0].strip()) or "your area"
    return _place(
        country_code=None,
        city=None,
        latitude=None,
        longitude=None,
        city_label=fallback,
        country_label="your country",
        hinted_region=None,
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_km = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return 2 * earth_km * asin(sqrt(a))


def _deal_point(deal: WeeklyDeal) -> tuple[float, float] | None:
    if deal.latitude is not None and deal.longitude is not None:
        if not (deal.latitude == 0.0 and deal.longitude == 0.0):
            return deal.latitude, deal.longitude
    return _centroid(deal.country_code, deal.city)


def _distance_km(place: SubscriberPlace, deal: WeeklyDeal) -> float | None:
    point = _deal_point(deal)
    if (
        place.latitude is None
        or place.longitude is None
        or point is None
    ):
        return None
    return _haversine_km(place.latitude, place.longitude, point[0], point[1])


def _deal_region_code(deal: WeeklyDeal) -> str | None:
    mapped = region_for_city(deal.country_code, deal.city)
    if mapped is None:
        return None
    return mapped[0]


def _tier(place: SubscriberPlace, deal: WeeklyDeal) -> str:
    if place.city and same_city(deal.city, place.city):
        return "city"
    distance = _distance_km(place, deal)
    if distance is not None and distance <= NEARBY_RADIUS_KM:
        return "nearby"
    if (
        place.region_code
        and _deal_region_code(deal) == place.region_code
        and normalize_country(deal.country_code) == (place.country_code or "")
    ):
        return "region"
    return "country"


def _sort_key(place: SubscriberPlace, deal: WeeklyDeal) -> tuple[int, float, float]:
    tier = _tier(place, deal)
    rank = {"city": 0, "nearby": 1, "region": 2, "country": 3}[tier]
    distance = 0.0 if tier == "city" else _distance_km(place, deal)
    if distance is None:
        distance = 1_000_000.0
    created = 0.0
    if deal.created_at is not None:
        created = deal.created_at.timestamp()
    return (rank, distance, -created)


def _is_expired(deal: WeeklyDeal, now: datetime) -> bool:
    if deal.expires_at is None:
        return False
    expires = deal.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires <= now


def _scope(place: SubscriberPlace, deals: list[WeeklyDeal]) -> str:
    if not deals:
        return "none"
    tiers = {_tier(place, deal) for deal in deals}
    if tiers == {"city"}:
        return "city"
    if "country" in tiers:
        return "country"
    if "region" in tiers:
        return "region"
    return "nearby"


def _state_has_kept_deals(place: SubscriberPlace, deals: list[WeeklyDeal]) -> bool:
    if not place.region_code or not place.country_code:
        return False
    country = place.country_code.upper()
    for deal in deals:
        if normalize_country(deal.country_code) != country:
            continue
        if _deal_region_code(deal) == place.region_code:
            return True
    return False


def review_candidates(
    deals: list[WeeklyDeal] | tuple[WeeklyDeal, ...],
    place: SubscriberPlace,
    *,
    limit: int = WEEKLY_DEAL_LIMIT,
    now: datetime | None = None,
) -> tuple[WeeklySelection, list[tuple[WeeklyDeal, str]]]:
    """Pick the email rows and record why every other candidate was left out."""
    moment = now or datetime.now(timezone.utc)
    excluded: list[tuple[WeeklyDeal, str]] = []
    local_currency = (
        DEFAULT_CURRENCY.get(place.country_code, "EUR")
        if place.country_code
        else "EUR"
    )
    if not place.country_code:
        for deal in deals:
            excluded.append((deal, "unknown_place"))
        selection = WeeklySelection(
            deals=[],
            scope="none",
            city_label=place.city_label,
            country_label=place.country_label,
            local_currency=local_currency,
            region_label=place.region_label,
        )
        return selection, excluded

    pool: list[WeeklyDeal] = []
    country = place.country_code.upper()
    for deal in deals:
        if _is_expired(deal, moment):
            excluded.append((deal, "expired"))
            continue
        if normalize_country(deal.country_code) != country:
            excluded.append((deal, "other_country"))
            continue
        pool.append(deal)

    ranked = sorted(pool, key=lambda deal: _sort_key(place, deal))
    kept = filter_kept_in_order(
        ranked,
        title=lambda deal: deal.title,
        merchant_name=lambda deal: deal.merchant_name,
        description=lambda deal: deal.description,
        venue_category=lambda deal: deal.venue_category,
        deal_price=lambda deal: deal.deal_price,
    )
    kept_ids = {deal.id for deal in kept}
    for deal in ranked:
        if deal.id in kept_ids:
            continue
        reason = rejection_reason(
            title=deal.title,
            description=deal.description,
            merchant_name=deal.merchant_name,
            venue_category=deal.venue_category,
            deal_price=deal.deal_price,
        )
        excluded.append((deal, reason.value if reason is not None else "duplicate"))

    if _state_has_kept_deals(place, kept):
        in_state: list[WeeklyDeal] = []
        for deal in kept:
            if _tier(place, deal) == "country":
                excluded.append((deal, "other_region"))
                continue
            in_state.append(deal)
        kept = in_state

    limited = kept[:limit]
    limited_ids = {deal.id for deal in limited}
    for deal in kept:
        if deal.id not in limited_ids:
            excluded.append((deal, "over_limit"))

    selection = WeeklySelection(
        deals=limited,
        scope=_scope(place, limited),
        city_label=place.city_label,
        country_label=place.country_label,
        local_currency=local_currency,
        region_label=place.region_label,
    )
    return selection, excluded


def select_weekly_deals(
    deals: list[WeeklyDeal] | tuple[WeeklyDeal, ...],
    place: SubscriberPlace,
    *,
    limit: int = WEEKLY_DEAL_LIMIT,
) -> WeeklySelection:
    selection, _excluded = review_candidates(deals, place, limit=limit)
    return selection


def _title_and_description(deal: Deal) -> tuple[str, str]:
    translations = list(deal.translations or [])
    if not translations:
        merchant = deal.merchant.name if deal.merchant else ""
        return merchant, ""
    preferred = next(
        (
            row
            for row in translations
            if (row.language_code or "").lower().startswith("en")
        ),
        translations[0],
    )
    return preferred.title or "", preferred.description or ""


def weekly_deal_from_model(deal: Deal) -> WeeklyDeal | None:
    merchant = deal.merchant
    loc = merchant.location if merchant else None
    if merchant is None or loc is None:
        return None
    if not (loc.country_code or "").strip() or not (loc.city or "").strip():
        return None
    title, description = _title_and_description(deal)
    lat = float(loc.latitude) if loc.latitude is not None else None
    lon = float(loc.longitude) if loc.longitude is not None else None
    outbound = deal.affiliate_url or deal.clean_url or deal.scraped_raw_url
    return WeeklyDeal(
        id=str(deal.id),
        title=title,
        description=description,
        merchant_name=merchant.name,
        venue_category=deal.venue_category,
        country_code=normalize_country(loc.country_code),
        city=loc.city.strip(),
        latitude=lat,
        longitude=lon,
        deal_price=Decimal(deal.deal_price) if deal.deal_price is not None else None,
        currency_code=(deal.currency_code or "").upper() or None,
        created_at=deal.created_at,
        expires_at=deal.expires_at,
        outbound_url=outbound,
    )


def country_deals_statement(country_code: str, *, city: str | None, limit: int):
    """Active, unexpired deals in one country. ``city`` narrows the SQL match."""
    now = datetime.now(timezone.utc)
    country = normalize_country(country_code)
    location_match = func.upper(Location.country_code) == country
    if city:
        city_key = city.lower().replace("-", " ").strip()
        location_match = and_(
            location_match,
            func.lower(func.replace(Location.city, "-", " ")) == city_key,
        )
    return (
        select(Deal)
        .where(Deal.is_active.is_(True))
        .where(Deal.deleted_at.is_(None))
        .where(or_(Deal.expires_at.is_(None), Deal.expires_at > now))
        .where(Deal.merchant.has(Merchant.location.has(location_match)))
        .options(
            selectinload(Deal.merchant).selectinload(Merchant.location),
            selectinload(Deal.translations),
        )
        .order_by(Deal.created_at.desc())
        .limit(limit)
    )


def fetch_weekly_deals(session: Session, place: SubscriberPlace) -> list[WeeklyDeal]:
    """Load candidates for one subscriber. Empty when the country is unknown."""
    if not place.country_code:
        return []
    by_id: dict[object, Deal] = {}
    if place.city:
        city_rows = session.scalars(
            country_deals_statement(
                place.country_code,
                city=place.city,
                limit=CITY_MATCH_CAP,
            )
        ).all()
        for deal in city_rows:
            by_id[deal.id] = deal
    country_rows = session.scalars(
        country_deals_statement(
            place.country_code,
            city=None,
            limit=WEEKLY_CANDIDATE_CAP,
        )
    ).all()
    for deal in country_rows:
        by_id.setdefault(deal.id, deal)
    mapped: list[WeeklyDeal] = []
    for deal in by_id.values():
        row = weekly_deal_from_model(deal)
        if row is not None:
            mapped.append(row)
    return mapped


def deal_public_url(deal: WeeklyDeal) -> str:
    """Canonical dineadeal.com deal page with Weekly Specials UTM tags."""
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    country = frontend_country_slug(deal.country_code)
    city = slugify_city(deal.city)
    return f"{base}/{country}/{city}/deals/{deal.id}?{urlencode(_UTM)}"


def _convert_amount(amount: Decimal, from_code: str, to_code: str) -> Decimal | None:
    source = from_code.upper()
    target = to_code.upper()
    if source == target:
        return amount
    if source not in CURRENCY_RATES or target not in CURRENCY_RATES:
        return None
    from_rate = Decimal(CURRENCY_RATES[source][0])
    to_rate = Decimal(CURRENCY_RATES[target][0])
    if from_rate == 0:
        return None
    return (amount / from_rate) * to_rate


def format_money(amount: Decimal, currency: str) -> str:
    """Symbol plus grouped digits. Zero-decimal currencies drop the cents."""
    code = currency.upper()
    symbol = CURRENCY_RATES.get(code, ("", code))[1]
    if code in _ZERO_DECIMAL:
        quantized = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        rendered = f"{int(quantized):,}"
    else:
        quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rendered = f"{quantized:,.2f}"
    if symbol and symbol != code:
        return f"{symbol}{rendered}"
    return f"{code} {rendered}"


def display_price(deal: WeeklyDeal, local_currency: str) -> str:
    """Local-currency price, or the percent / free label when price is unset."""
    promo = promotional_price_label(deal.title, deal.description)
    amount = deal.deal_price
    if amount is None or amount <= 0:
        return promo or ""
    source = (deal.currency_code or local_currency).upper()
    converted = _convert_amount(Decimal(amount), source, local_currency)
    if converted is None:
        return format_money(Decimal(amount), source)
    formatted = format_money(converted, local_currency)
    if promo and "%" in promo:
        return f"{formatted} ({promo})"
    return formatted


def _intro(selection: WeeklySelection) -> str:
    place = selection.place_label
    country = selection.country_label
    if selection.scope == "none":
        if selection.region_label:
            return (
                f"No new local deals this week in {place}. "
                f"We only email offers from {place}, nearby towns, "
                f"{selection.region_label}, and the rest of {country}. "
                "We'll try again next Friday."
            )
        return (
            f"No new local deals this week in {place}. "
            f"We only email offers from {place}, nearby towns, and the rest of {country}. "
            "We'll try again next Friday."
        )
    if selection.scope == "city":
        return f"Here are this week's dining deals for {place}:"
    if selection.scope == "nearby":
        return f"Here are this week's dining deals for {place} and nearby towns:"
    if selection.scope == "region" and selection.region_label:
        return (
            f"Here are this week's dining deals for {place} "
            f"and the rest of {selection.region_label}:"
        )
    if selection.scope == "country":
        if selection.city_label:
            return (
                f"Here are this week's dining deals for {place}, "
                f"including a few from elsewhere in {country}:"
            )
        return f"Here are this week's dining deals for {country}:"
    return f"Here are this week's dining deals for {place}:"


def _unsubscribe_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/newsletter/unsubscribe?token={quote(token)}"


def _html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_weekly_email(
    subscriber: NewsletterSubscriber,
    selection: WeeklySelection,
) -> tuple[str, str, str]:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    unsub = _unsubscribe_url(subscriber.unsubscribe_token)
    first = _one_line(subscriber.name.split()[0] if subscriber.name else "there")
    place = _one_line(selection.place_label)
    intro = _intro(selection)
    if selection.scope == "none":
        subject = f"Dine A Deal — no new local deals in {place} this week"
    else:
        subject = f"Dine A Deal — this week's specials in {place}"

    lines = [f"Hi {first},", "", intro, ""]
    html_items: list[str] = []
    for deal in selection.deals:
        title = _one_line(deal.title)
        merchant = _one_line(deal.merchant_name)
        city = _one_line(deal.city)
        price = display_price(deal, selection.local_currency)
        href = deal_public_url(deal)
        show_price = bool(price) and price.lower() not in title.lower()
        price_bit = f" — {price}" if show_price else ""
        lines.append(f"• {title} — {merchant}, {city}{price_bit}")
        lines.append(f"  {href}")
        lines.append("")
        html_items.append(
            "<li style=\"margin:0 0 12px\">"
            f'<a href="{_html_escape(href)}" style="color:#7a1f2b;font-weight:600">'
            f"{_html_escape(title)}</a>"
            "<br/><span style=\"color:#444\">"
            f"{_html_escape(merchant)} · {_html_escape(city)}"
            f"{(' · ' + _html_escape(price)) if show_price else ''}"
            "</span></li>"
        )

    lines.extend(
        [
            "—",
            "You're receiving this because you signed up for Weekly Specials.",
            f"Unsubscribe (keeps your details on file): {unsub}",
            "",
            f"Browse all deals: {base}",
        ]
    )
    text_body = "\n".join(lines)
    list_html = (
        f'<ul style="padding-left:18px">{"".join(html_items)}</ul>'
        if html_items
        else ""
    )
    html_body = f"""<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;color:#1a1a1a;max-width:560px;margin:0 auto;padding:24px">
  <h1 style="font-family:Arial,sans-serif;color:#7a1f2b;font-size:22px;text-transform:uppercase;letter-spacing:0.04em">
    Dine A Deal
  </h1>
  <p>Hi {_html_escape(first)},</p>
  <p>{_html_escape(intro)}</p>
  {list_html}
  <p style="margin-top:28px;font-size:13px;color:#666">
    You're receiving this because you signed up for Weekly Specials every Friday.
  </p>
  <p style="font-size:13px">
    <a href="{_html_escape(unsub)}">Unsubscribe</a>
    — we'll stop emails but keep your details on file so you can subscribe again anytime.
  </p>
  <p style="font-size:13px"><a href="{_html_escape(base)}">Browse Dine A Deal</a></p>
</body></html>"""
    return subject, text_body, html_body


def backfill_subscriber_location(subscriber: NewsletterSubscriber) -> bool:
    """Fill only null country, city, and region. Existing values stay put.

    Called before a Weekly Specials send so older free-text signups pick up
    a city and state from the location string and the city map. The row is
    written on the same commit as a successful send.
    """
    place = resolve_subscriber_place(
        subscriber.country_code,
        subscriber.city,
        subscriber.location,
        subscriber.region,
    )
    changed = False
    if not (subscriber.country_code or "").strip() and place.country_code:
        subscriber.country_code = place.country_code.lower()
        changed = True
    if not (subscriber.city or "").strip() and place.city:
        subscriber.city = place.city
        changed = True
    if not (subscriber.region or "").strip() and place.region_code:
        subscriber.region = place.region_code
        changed = True
    return changed


def render_weekly_issue(
    subscriber: NewsletterSubscriber,
    deals: list[WeeklyDeal],
) -> tuple[str, str, str, WeeklySelection, list[tuple[WeeklyDeal, str]]]:
    """Build the email for a subscriber from in-memory deals. Does not send."""
    place = resolve_subscriber_place(
        subscriber.country_code,
        subscriber.city,
        subscriber.location,
        subscriber.region,
    )
    selection, excluded = review_candidates(deals, place)
    subject, text_body, html_body = build_weekly_email(subscriber, selection)
    return subject, text_body, html_body, selection, excluded


def send_weekly_special_to_subscriber(
    session: Session,
    subscriber: NewsletterSubscriber,
) -> dict[str, object]:
    if not subscriber.is_subscribed:
        return {"email": subscriber.email, "skipped": True, "reason": "unsubscribed"}

    backfill_subscriber_location(subscriber)
    place = resolve_subscriber_place(
        subscriber.country_code,
        subscriber.city,
        subscriber.location,
        subscriber.region,
    )
    deals = fetch_weekly_deals(session, place)
    selection, excluded = review_candidates(deals, place)
    subject, text_body, html_body = build_weekly_email(subscriber, selection)
    ok = send_email(
        to_email=subscriber.email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    if ok:
        subscriber.last_emailed_at = datetime.now(timezone.utc)
        session.commit()
    logger.info(
        "Weekly specials for %s place=%s scope=%s deals=%s excluded=%s",
        subscriber.email,
        place.place_label,
        selection.scope,
        len(selection.deals),
        len(excluded),
    )
    return {
        "email": subscriber.email,
        "sent": ok,
        "deal_count": len(selection.deals),
        "scope": selection.scope,
        "country_code": place.country_code,
    }
