"""Extra regional catchment hubs (wine country, state interiors) beyond top metros."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.scrapers.wine_regions import (
    WINE_REGIONS,
    is_wine_region_hub,
    wine_region_coords,
    wine_region_hubs,
    wine_region_winery_caps,
)

# Non-wine regional hubs (metros already in MARKET_CITIES — these fill gaps).
NON_WINE_CATCHMENT_HUBS: dict[str, list[str]] = {
    "US": [
        "Oakland",
        "Fresno",
        "Palm Springs",
        "Long Beach",
    ],
    "IE": [
        "Killarney",
        "Westport",
    ],
}

NON_WINE_CATCHMENT_COORDS: dict[tuple[str, str], tuple[float, float]] = {
    ("US", "Oakland"): (37.8044, -122.2712),
    ("US", "Fresno"): (36.7378, -119.7871),
    ("US", "Palm Springs"): (33.8303, -116.5453),
    ("US", "Long Beach"): (33.7701, -118.1937),
    ("IE", "Killarney"): (52.0599, -9.5044),
    ("IE", "Westport"): (53.8000, -9.5167),
}


def _target_market_codes() -> set[str]:
    from app.scrapers.markets import TARGET_MARKETS

    return {code.strip().upper() for code in TARGET_MARKETS}


def _build_catchment_hubs() -> dict[str, list[str]]:
    allowed = _target_market_codes()
    merged: dict[str, list[str]] = {}
    countries = (set(NON_WINE_CATCHMENT_HUBS) | set(WINE_REGIONS)) & allowed
    for code in countries:
        names: list[str] = []
        seen: set[str] = set()
        for name in wine_region_hubs(code) + NON_WINE_CATCHMENT_HUBS.get(code, []):
            title = name.strip().title()
            if title in seen:
                continue
            seen.add(title)
            names.append(title)
        if names:
            merged[code] = names
    return merged


CATCHMENT_HUBS: dict[str, list[str]] = _build_catchment_hubs()

CATCHMENT_COORDS: dict[tuple[str, str], tuple[float, float]] = {
    **wine_region_coords(),
    **NON_WINE_CATCHMENT_COORDS,
}


@dataclass(frozen=True)
class HubCatchmentProfile:
    """Per-hub discovery bias — e.g. Napa pulls wineries, not 10x Domino's."""

    winery_boost: bool = False
    category_cap_overrides: dict[str, int] = field(default_factory=dict)
    prefer_independents: bool = True


def _build_wine_profiles() -> dict[tuple[str, str], HubCatchmentProfile]:
    allowed = _target_market_codes()
    caps = wine_region_winery_caps()
    profiles: dict[tuple[str, str], HubCatchmentProfile] = {}
    for key, cap in caps.items():
        if key[0] not in allowed:
            continue
        profiles[key] = HubCatchmentProfile(
            winery_boost=True,
            category_cap_overrides={"Wine Farms & Entertainment Venues": cap},
        )
    return profiles


HUB_CATCHMENT_PROFILES: dict[tuple[str, str], HubCatchmentProfile] = _build_wine_profiles()


def catchment_cities_for(country_code: str, existing: list[str]) -> list[str]:
    """Return extra regional hubs not already in the country's city list."""
    code = country_code.strip().upper()
    seen = {c.strip().title() for c in existing}
    extras: list[str] = []
    for city in CATCHMENT_HUBS.get(code, []):
        title = city.strip().title()
        if title not in seen:
            seen.add(title)
            extras.append(title)
    return extras


def hub_catchment_profile(country_code: str, hub_city: str) -> HubCatchmentProfile | None:
    key = (country_code.strip().upper(), hub_city.strip().title())
    if key in HUB_CATCHMENT_PROFILES:
        return HUB_CATCHMENT_PROFILES[key]
    if is_wine_region_hub(country_code, hub_city):
        return HubCatchmentProfile(
            winery_boost=True,
            category_cap_overrides={"Wine Farms & Entertainment Venues": 14},
        )
    return None
