"""Country and city name normalization shared by the API and ingest."""

from __future__ import annotations

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


# Stringified missing values ("null", Python "None") and the scrape fallback.
# Matched after lowercasing and turning hyphens/underscores into spaces.
PLACEHOLDER_CITY_NAMES: frozenset[str] = frozenset(
    {"null", "none", "undefined", "unknown"}
)


def is_placeholder_city(city: str | None) -> bool:
    """True for empty or sentinel city names that must not become public URLs."""
    if city is None:
        return True
    normalized = " ".join(city.replace("-", " ").replace("_", " ").split()).strip().lower()
    return not normalized or normalized in PLACEHOLDER_CITY_NAMES
