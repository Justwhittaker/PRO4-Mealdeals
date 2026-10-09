"""Continental scrape zones — bite-size worldwide refresh.

A zone is one Celery task. Observed pace on the NUC is about four minutes per
city, and the soft time limit is four hours, so a task stays at or under
``MAX_ZONE_AREAS`` cities (about three hours, with room before the limit).
"""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from app.scrapers.markets import TARGET_MARKETS, iter_market_areas

# About four minutes per city was west_eu_core's pace (60 cities in 14,411s).
# 40 cities is under three hours, so the 4h soft limit stays a backstop.
MAX_ZONE_AREAS = 40

# Six scrape processes on a 12-core NUC that sits idle at concurrency 2.
# Capped so a typo cannot open dozens of Overpass clients. Maintenance is a
# separate worker and does not count against this.
DEFAULT_SCRAPE_CONCURRENCY = 6
MAX_SCRAPE_CONCURRENCY = 8

SCRAPE_ZONES: dict[str, dict[str, str]] = {
    "eastern_europe": {
        "label": "Eastern Europe",
        "description": "Central / eastern EU",
        "family": "eastern_europe",
        "size_class": "small",
    },
    "mena": {
        "label": "Middle East & North Africa",
        "description": "Gulf, Levant, Turkey",
        "family": "mena",
        "size_class": "small",
    },
    "latin_america": {
        "label": "Latin America",
        "description": "Central & South America",
        "family": "latin_america",
        "size_class": "small",
    },
    "west_east_africa": {
        "label": "West & East Africa",
        "description": "West and east African hubs",
        "family": "africa",
        "size_class": "medium",
    },
    "southern_africa": {
        "label": "Southern Africa",
        "description": "South Africa and neighbouring hubs",
        "family": "africa",
        "size_class": "medium",
    },
    "se_asia": {
        "label": "Southeast Asia",
        "description": "Mainland and island Southeast Asia",
        "family": "asia",
        "size_class": "medium",
    },
    "east_south_asia": {
        "label": "East & South Asia",
        "description": "China, Japan, Korea, India, Pakistan",
        "family": "asia",
        "size_class": "medium",
    },
    "australia": {
        "label": "Australia",
        "description": "Australian metros and wine regions",
        "family": "oceania",
        "size_class": "medium",
    },
    "pacific": {
        "label": "New Zealand & Pacific",
        "description": "NZ and Pacific island hubs",
        "family": "oceania",
        "size_class": "medium",
    },
    "british_isles": {
        "label": "British Isles (large)",
        "description": "UK + Ireland",
        "family": "western_europe",
        "size_class": "large",
    },
    "iberia": {
        "label": "Iberia (large)",
        "description": "Spain and Portugal",
        "family": "western_europe",
        "size_class": "large",
    },
    "italy_adriatic": {
        "label": "Italy & Adriatic (large)",
        "description": "Italy, Greece, and the Adriatic",
        "family": "western_europe",
        "size_class": "large",
    },
    "canada": {
        "label": "Canada (large)",
        "description": "Canadian metros",
        "family": "north_america",
        "size_class": "large",
    },
    "mexico_caribbean": {
        "label": "Mexico & Caribbean (large)",
        "description": "Mexico, Caribbean, and US territories",
        "family": "north_america",
        "size_class": "large",
    },
    "us_east": {
        "label": "US East & Midwest (large)",
        "description": "Eastern and central US metros",
        "family": "north_america",
        "size_class": "large",
    },
    "us_west": {
        "label": "US West (large)",
        "description": "Western US metros and wine regions",
        "family": "north_america",
        "size_class": "large",
    },
    "france_benelux": {
        "label": "France & Benelux (large)",
        "description": "France, Netherlands, Belgium",
        "family": "western_europe",
        "size_class": "large",
    },
    "dach_nordics": {
        "label": "DACH & Nordics (large)",
        "description": "Germany, Alps, and the Nordics",
        "family": "western_europe",
        "size_class": "large",
    },
}

ZONE_FAMILY_LABELS: dict[str, str] = {
    "north_america": "North America & Caribbean (large)",
    "western_europe": "Western Europe (large)",
    "eastern_europe": "Eastern Europe",
    "mena": "Middle East & North Africa",
    "latin_america": "Latin America",
    "africa": "Africa",
    "asia": "Asia",
    "oceania": "Oceania & Pacific",
}

_COUNTRY_ZONE: dict[str, str] = {
    "US": "us_east",
    "CA": "canada",
    "MX": "mexico_caribbean",
    "BS": "mexico_caribbean",
    "JM": "mexico_caribbean",
    "BZ": "mexico_caribbean",
    "GD": "mexico_caribbean",
    "TT": "mexico_caribbean",
    "BB": "mexico_caribbean",
    "AG": "mexico_caribbean",
    "KN": "mexico_caribbean",
    "VC": "mexico_caribbean",
    "PR": "mexico_caribbean",
    "VI": "mexico_caribbean",
    "AR": "latin_america",
    "BR": "latin_america",
    "CL": "latin_america",
    "CO": "latin_america",
    "GY": "latin_america",
    "GB": "british_isles",
    "IE": "british_isles",
    "ES": "iberia",
    "PT": "iberia",
    "IT": "italy_adriatic",
    "GR": "italy_adriatic",
    "HR": "italy_adriatic",
    "MT": "italy_adriatic",
    "SI": "italy_adriatic",
    "FR": "france_benelux",
    "NL": "france_benelux",
    "BE": "france_benelux",
    "DE": "dach_nordics",
    "CH": "dach_nordics",
    "AT": "dach_nordics",
    "NO": "dach_nordics",
    "SE": "dach_nordics",
    "DK": "dach_nordics",
    "FI": "dach_nordics",
    "IS": "dach_nordics",
    "PL": "eastern_europe",
    "CZ": "eastern_europe",
    "SK": "eastern_europe",
    "NG": "west_east_africa",
    "KE": "west_east_africa",
    "GH": "west_east_africa",
    "CM": "west_east_africa",
    "RW": "west_east_africa",
    "SL": "west_east_africa",
    "SS": "west_east_africa",
    "UG": "west_east_africa",
    "LR": "west_east_africa",
    "GM": "west_east_africa",
    "ZA": "southern_africa",
    "NA": "southern_africa",
    "BW": "southern_africa",
    "ZW": "southern_africa",
    "ZM": "southern_africa",
    "MW": "southern_africa",
    "SZ": "southern_africa",
    "LS": "southern_africa",
    "AE": "mena",
    "IL": "mena",
    "JO": "mena",
    "QA": "mena",
    "TR": "mena",
    "EG": "mena",
    "MA": "mena",
    "TN": "mena",
    "PH": "se_asia",
    "TH": "se_asia",
    "ID": "se_asia",
    "MY": "se_asia",
    "VN": "se_asia",
    "SG": "se_asia",
    "CN": "east_south_asia",
    "JP": "east_south_asia",
    "KR": "east_south_asia",
    "IN": "east_south_asia",
    "PK": "east_south_asia",
    "AU": "australia",
    "NZ": "pacific",
    "FJ": "pacific",
    "PG": "pacific",
    "SB": "pacific",
    "VU": "pacific",
    "WS": "pacific",
    "KI": "pacific",
    "NR": "pacific",
    "MH": "pacific",
    "FM": "pacific",
    "PW": "pacific",
    "TO": "pacific",
    "TV": "pacific",
    "GU": "pacific",
    "AS": "pacific",
    "MP": "pacific",
}

# Western and south-central US hubs. The rest of the US stays on us_east.
_US_WEST_CITIES = frozenset(
    {
        "Los Angeles",
        "Phoenix",
        "San Diego",
        "San Jose",
        "Houston",
        "San Antonio",
        "Dallas",
        "Austin",
        "San Francisco",
        "Seattle",
        "Denver",
        "Portland",
        "Las Vegas",
        "Sacramento",
        "Salt Lake City",
        "Honolulu",
        "Napa Valley",
        "Sonoma",
        "Santa Barbara Wine Country",
        "Willamette Valley",
        "Walla Walla Valley",
        "Paso Robles",
        "Texas Hill Country Wine",
        "Monterey Wine Country",
        "Oakland",
        "Fresno",
        "Palm Springs",
        "Long Beach",
    }
)

_CITY_ZONE: dict[tuple[str, str], str] = {
    ("US", city): "us_west" for city in _US_WEST_CITIES
}

# Wall-clock hours in Europe/Dublin, including across the October/March DST change.
SCRAPE_TIMEZONE_NAME = "Europe/Dublin"
SCRAPE_TIMEZONE = ZoneInfo(SCRAPE_TIMEZONE_NAME)
ZONE_CYCLE_BASE_HOURS: tuple[int, ...] = (7, 19)
# One hour before the next cycle (06:00 covers the previous 19:00, 18:00 covers 07:00).
DIGEST_HOURS: tuple[int, ...] = (6, 18)

# Smaller tasks first. Large families stay a trailing block.
ZONE_ORDER: list[str] = [
    "eastern_europe",
    "mena",
    "latin_america",
    "west_east_africa",
    "southern_africa",
    "se_asia",
    "east_south_asia",
    "australia",
    "pacific",
    "british_isles",
    "iberia",
    "italy_adriatic",
    "canada",
    "mexico_caribbean",
    "us_east",
    "us_west",
    "france_benelux",
    "dach_nordics",
]

# 10 minutes fills six workers quickly without publishing every zone at once.
# 18 zones are all queued inside three hours.
ZONE_BEAT_STAGGER_MINUTES = 10


def _beat_slots_for_order(order: list[str]) -> dict[str, tuple[int, int]]:
    """Stagger from cycle base: (minute, hour_offset)."""
    slots: dict[str, tuple[int, int]] = {}
    for index, zone_id in enumerate(order):
        offset_minutes = index * ZONE_BEAT_STAGGER_MINUTES
        slots[zone_id] = (offset_minutes % 60, offset_minutes // 60)
    return slots


ZONE_BEAT_SLOTS: dict[str, tuple[int, int]] = _beat_slots_for_order(ZONE_ORDER)

ZONE_TASK_EXPIRES_SECONDS: int = (11 * 60 * 60) + (55 * 60)
ZONE_TASK_SOFT_TIME_LIMIT_SECONDS: int = 4 * 60 * 60
ZONE_TASK_TIME_LIMIT_SECONDS: int = (4 * 60 * 60) + (15 * 60)
REDIS_VISIBILITY_TIMEOUT_SECONDS: int = 8 * 60 * 60

SCRAPE_QUEUE = "scrape"
MAINTENANCE_QUEUE = "maintenance"

LARGE_ZONE_FAMILIES: tuple[str, ...] = ("north_america", "western_europe")


def scrape_concurrency(raw: str | None = None) -> int:
    """Scrape worker processes. Maintenance stays on its own worker."""
    if raw is None:
        raw = os.environ.get("SCRAPE_CONCURRENCY", "")
    text = raw.strip()
    if not text:
        return DEFAULT_SCRAPE_CONCURRENCY
    try:
        value = int(text)
    except ValueError:
        return DEFAULT_SCRAPE_CONCURRENCY
    return min(MAX_SCRAPE_CONCURRENCY, max(1, value))


def zone_family(zone_id: str) -> str:
    meta = SCRAPE_ZONES.get(zone_id.strip().lower()) or {}
    return str(meta.get("family") or zone_id)


def zone_size_class(zone_id: str) -> str:
    meta = SCRAPE_ZONES.get(zone_id.strip().lower()) or {}
    return str(meta.get("size_class") or "medium")


def zone_for_country(country_code: str) -> str:
    """Default zone for a country. Some US cities override this."""
    code = country_code.strip().upper()
    zone = _COUNTRY_ZONE.get(code)
    if zone is None:
        raise KeyError(f"No scrape zone configured for country {code}")
    return zone


def zone_for_area(country_code: str, city: str) -> str:
    code = country_code.strip().upper()
    override = _CITY_ZONE.get((code, city.strip()))
    if override:
        return override
    return zone_for_country(code)


def iter_zone_areas(zone_id: str) -> list[tuple[str, str]]:
    """Hub cities belonging to one beat task."""
    zone = zone_id.strip().lower()
    if zone not in SCRAPE_ZONES:
        return []
    return [
        (country, city)
        for country, city in iter_market_areas(list(TARGET_MARKETS))
        if zone_for_area(country, city) == zone
    ]


def markets_for_zone(zone_id: str) -> list[str]:
    return sorted({country for country, _city in iter_zone_areas(zone_id)})


def validate_zone_coverage() -> None:
    """Ensure every market city is in one known zone, and no zone is too big."""
    missing = [c for c in TARGET_MARKETS if c not in _COUNTRY_ZONE]
    if missing:
        raise RuntimeError(f"Countries missing scrape zone: {missing}")
    unknown = sorted({zone for zone in _COUNTRY_ZONE.values() if zone not in SCRAPE_ZONES})
    if unknown:
        raise RuntimeError(f"Countries map to unknown scrape zones: {unknown}")
    if set(ZONE_ORDER) != set(SCRAPE_ZONES):
        raise RuntimeError("ZONE_ORDER and SCRAPE_ZONES keys must match")
    if set(ZONE_BEAT_SLOTS) != set(ZONE_ORDER):
        raise RuntimeError("ZONE_BEAT_SLOTS and ZONE_ORDER keys must match")

    counts: dict[str, int] = {zone_id: 0 for zone_id in SCRAPE_ZONES}
    for country, city in iter_market_areas(list(TARGET_MARKETS)):
        zone = zone_for_area(country, city)
        if zone not in SCRAPE_ZONES:
            raise RuntimeError(f"{country}/{city} maps to unknown zone {zone}")
        counts[zone] += 1
    empty = [zone_id for zone_id, count in counts.items() if count == 0]
    if empty:
        raise RuntimeError(f"Zones have no cities: {empty}")
    too_big = [
        f"{zone_id}={count}"
        for zone_id, count in counts.items()
        if count > MAX_ZONE_AREAS
    ]
    if too_big:
        raise RuntimeError(
            f"Zones exceed {MAX_ZONE_AREAS} cities (soft time limit): {too_big}"
        )
