"""Continental scrape zones — bite-size worldwide refresh."""

from __future__ import annotations

from app.scrapers.markets import MARKET_CITIES, TARGET_MARKETS, iter_market_areas

# Eight continental zones. Every TARGET_MARKET country appears exactly once.
SCRAPE_ZONES: dict[str, dict[str, str]] = {
    "north_america": {
        "label": "North America & Caribbean",
        "description": "US, Canada, Mexico, Caribbean hubs",
    },
    "latin_america": {
        "label": "Latin America",
        "description": "Central & South America",
    },
    "western_europe": {
        "label": "Western Europe",
        "description": "UK, Ireland, EU west, Nordics",
    },
    "eastern_europe": {
        "label": "Eastern Europe",
        "description": "Central / eastern EU",
    },
    "africa": {
        "label": "Africa",
        "description": "Sub-Saharan & north Africa hubs",
    },
    "mena": {
        "label": "Middle East & North Africa",
        "description": "Gulf, Levant, Turkey",
    },
    "asia": {
        "label": "Asia",
        "description": "South, East & Southeast Asia",
    },
    "oceania": {
        "label": "Oceania & Pacific",
        "description": "Australia, NZ, Pacific islands",
    },
}

_COUNTRY_ZONE: dict[str, str] = {
    # North America & Caribbean
    "US": "north_america",
    "CA": "north_america",
    "MX": "north_america",
    "BS": "north_america",
    "JM": "north_america",
    "BZ": "north_america",
    "GD": "north_america",
    "TT": "north_america",
    "BB": "north_america",
    "AG": "north_america",
    "KN": "north_america",
    "VC": "north_america",
    # Latin America
    "AR": "latin_america",
    "BR": "latin_america",
    "CL": "latin_america",
    "CO": "latin_america",
    "GY": "latin_america",
    # Western Europe
    "GB": "western_europe",
    "IE": "western_europe",
    "FR": "western_europe",
    "DE": "western_europe",
    "ES": "western_europe",
    "PT": "western_europe",
    "NL": "western_europe",
    "BE": "western_europe",
    "CH": "western_europe",
    "AT": "western_europe",
    "IT": "western_europe",
    "GR": "western_europe",
    "NO": "western_europe",
    "SE": "western_europe",
    "DK": "western_europe",
    "FI": "western_europe",
    "IS": "western_europe",
    "MT": "western_europe",
    "HR": "western_europe",
    "SI": "western_europe",
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
}

# Celery Beat slot: (minute, hour_offset) within each 6-hour cycle (0,6,12,18 UTC).
# Eight zones fire every 15 minutes: 00:00 → 01:45, then 06:00 → 07:45, etc.
ZONE_BEAT_SLOTS: dict[str, tuple[int, int]] = {
    "north_america": (0, 0),
    "latin_america": (15, 0),
    "western_europe": (30, 0),
    "eastern_europe": (45, 0),
    "africa": (0, 1),
    "mena": (15, 1),
    "asia": (30, 1),
    "oceania": (45, 1),
}

ZONE_ORDER: list[str] = [
    "north_america",
    "latin_america",
    "western_europe",
    "eastern_europe",
    "africa",
    "mena",
    "asia",
    "oceania",
]


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
    """Ensure every TARGET_MARKET is assigned to a zone."""
    missing = [c for c in TARGET_MARKETS if c not in _COUNTRY_ZONE]
    if missing:
        raise RuntimeError(f"Countries missing scrape zone: {missing}")
