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
