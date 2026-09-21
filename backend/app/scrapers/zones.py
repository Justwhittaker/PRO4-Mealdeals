"""Continental scrape zones — bite-size worldwide refresh."""

from __future__ import annotations

from app.scrapers.markets import MARKET_CITIES, TARGET_MARKETS, iter_market_areas

# Scrape task zones. Every TARGET_MARKET country appears in exactly one zone.
# North America and Western Europe are split into smaller tasks but tagged
# size_class=large / family=… so digests and scheduling still treat them as
# the heavy "large scrape" block at the end of each cycle.
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
    "africa": {
        "label": "Africa",
        "description": "Sub-Saharan & north Africa hubs",
        "family": "africa",
        "size_class": "medium",
    },
    "asia": {
        "label": "Asia",
        "description": "South, East & Southeast Asia",
        "family": "asia",
        "size_class": "medium",
    },
    "oceania": {
        "label": "Oceania & Pacific",
        "description": "Australia, NZ, Pacific islands",
        "family": "oceania",
        "size_class": "medium",
    },
    # --- Large scrape family: North America (split for queue health) ---
    "canada_mexico_caribbean": {
        "label": "Canada / Mexico / Caribbean (large)",
        "description": "CA, MX, and Caribbean hubs — NA large-scrape split",
        "family": "north_america",
        "size_class": "large",
    },
    "us": {
        "label": "United States (large)",
        "description": "US metros — NA large-scrape split",
        "family": "north_america",
        "size_class": "large",
    },
    # --- Large scrape family: Western Europe (split for queue health) ---
    "british_isles": {
        "label": "British Isles (large)",
        "description": "UK + Ireland — WE large-scrape split",
        "family": "western_europe",
        "size_class": "large",
    },
    "south_europe": {
        "label": "Southern Europe (large)",
        "description": "Iberia, Italy, Greece, Adriatic — WE large-scrape split",
        "family": "western_europe",
        "size_class": "large",
    },
    "west_eu_core": {
        "label": "West EU core (large)",
        "description": "France, Germany, Benelux, Alps, Nordics — WE large-scrape split",
        "family": "western_europe",
        "size_class": "large",
    },
}

# Human labels for digest rollups of split large families.
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
    # North America large-scrape splits
    "US": "us",
    "CA": "canada_mexico_caribbean",
    "MX": "canada_mexico_caribbean",
    "BS": "canada_mexico_caribbean",
    "JM": "canada_mexico_caribbean",
    "BZ": "canada_mexico_caribbean",
    "GD": "canada_mexico_caribbean",
    "TT": "canada_mexico_caribbean",
    "BB": "canada_mexico_caribbean",
    "AG": "canada_mexico_caribbean",
    "KN": "canada_mexico_caribbean",
    "VC": "canada_mexico_caribbean",
    # US territories (when present in TARGET_MARKETS)
    "PR": "canada_mexico_caribbean",
    "VI": "canada_mexico_caribbean",
    # Latin America
    "AR": "latin_america",
    "BR": "latin_america",
    "CL": "latin_america",
    "CO": "latin_america",
    "GY": "latin_america",
    # Western Europe large-scrape splits
    "GB": "british_isles",
    "IE": "british_isles",
    "ES": "south_europe",
    "PT": "south_europe",
    "IT": "south_europe",
    "GR": "south_europe",
    "HR": "south_europe",
    "MT": "south_europe",
    "SI": "south_europe",
    "FR": "west_eu_core",
    "DE": "west_eu_core",
    "NL": "west_eu_core",
    "BE": "west_eu_core",
    "CH": "west_eu_core",
    "AT": "west_eu_core",
    "NO": "west_eu_core",
    "SE": "west_eu_core",
    "DK": "west_eu_core",
    "FI": "west_eu_core",
    "IS": "west_eu_core",
    # Eastern Europe
    "PL": "eastern_europe",
    "CZ": "eastern_europe",
    "SK": "eastern_europe",
    # Africa (sub-Saharan focus)
    "ZA": "africa",
    "NG": "africa",
    "KE": "africa",
    "GH": "africa",
    "CM": "africa",
    "BW": "africa",
    "NA": "africa",
    "RW": "africa",
    "SL": "africa",
    "SS": "africa",
    "SZ": "africa",
    "UG": "africa",
    "ZM": "africa",
    "ZW": "africa",
    "LR": "africa",
    "LS": "africa",
    "GM": "africa",
    "MW": "africa",
    # MENA
    "AE": "mena",
    "IL": "mena",
    "JO": "mena",
    "QA": "mena",
    "TR": "mena",
    "EG": "mena",
    "MA": "mena",
    "TN": "mena",
    # Asia
    "CN": "asia",
    "JP": "asia",
    "KR": "asia",
    "IN": "asia",
    "ID": "asia",
    "PH": "asia",
    "TH": "asia",
    "MY": "asia",
    "SG": "asia",
    "VN": "asia",
    "PK": "asia",
    # Oceania & Pacific
    "AU": "oceania",
    "NZ": "oceania",
    "FJ": "oceania",
    "PG": "oceania",
    "SB": "oceania",
    "VU": "oceania",
    "WS": "oceania",
    "KI": "oceania",
    "NR": "oceania",
    "MH": "oceania",
    "FM": "oceania",
    "PW": "oceania",
    "TO": "oceania",
    "TV": "oceania",
    "GU": "oceania",
    "AS": "oceania",
    "MP": "oceania",
}

# Twice-daily cycle bases (UTC).
ZONE_CYCLE_BASE_HOURS: tuple[int, ...] = (6, 18)

# Rest-of-world first, then NA/WE large-scrape splits (smaller pieces before
# heavier ones inside that large block).
ZONE_ORDER: list[str] = [
    "eastern_europe",
    "mena",
    "latin_america",
    "africa",
    "asia",
    "oceania",
    # Large scrapes (NA + WE families) — always after the rest of the world
    "british_isles",
    "south_europe",
    "canada_mexico_caribbean",
    "us",
    "west_eu_core",
]


def _beat_slots_for_order(order: list[str]) -> dict[str, tuple[int, int]]:
    """15-minute stagger from cycle base: (minute, hour_offset)."""
    slots: dict[str, tuple[int, int]] = {}
    for index, zone_id in enumerate(order):
        offset_minutes = index * 15
        slots[zone_id] = (offset_minutes % 60, offset_minutes // 60)
    return slots


ZONE_BEAT_SLOTS: dict[str, tuple[int, int]] = _beat_slots_for_order(ZONE_ORDER)

# Keep queued zone tasks alive almost until the next twice-daily cycle (12h).
ZONE_TASK_EXPIRES_SECONDS: int = (11 * 60 * 60) + (55 * 60)

LARGE_ZONE_FAMILIES: tuple[str, ...] = ("north_america", "western_europe")


def zone_family(zone_id: str) -> str:
    meta = SCRAPE_ZONES.get(zone_id.strip().lower()) or {}
    return str(meta.get("family") or zone_id)


def zone_size_class(zone_id: str) -> str:
    meta = SCRAPE_ZONES.get(zone_id.strip().lower()) or {}
    return str(meta.get("size_class") or "medium")


def zone_for_country(country_code: str) -> str:
    code = country_code.strip().upper()
    zone = _COUNTRY_ZONE.get(code)
    if zone is None:
        raise KeyError(f"No scrape zone configured for country {code}")
    return zone


def markets_for_zone(zone_id: str) -> list[str]:
    zone = zone_id.strip().lower()
    return sorted(
        code for code in TARGET_MARKETS if _COUNTRY_ZONE.get(code) == zone
    )


def iter_zone_areas(zone_id: str) -> list[tuple[str, str]]:
    """Hub cities belonging to a continental zone."""
    markets = markets_for_zone(zone_id)
    return iter_market_areas(markets)


def validate_zone_coverage() -> None:
    """Ensure every TARGET_MARKET is assigned to a known zone."""
    missing = [c for c in TARGET_MARKETS if c not in _COUNTRY_ZONE]
    if missing:
        raise RuntimeError(f"Countries missing scrape zone: {missing}")
    unknown = sorted(
        {
            zone
            for zone in _COUNTRY_ZONE.values()
            if zone not in SCRAPE_ZONES
        }
    )
    if unknown:
        raise RuntimeError(f"Countries map to unknown scrape zones: {unknown}")
    if set(ZONE_ORDER) != set(SCRAPE_ZONES):
        raise RuntimeError("ZONE_ORDER and SCRAPE_ZONES keys must match")
    if set(ZONE_BEAT_SLOTS) != set(ZONE_ORDER):
        raise RuntimeError("ZONE_BEAT_SLOTS and ZONE_ORDER keys must match")
