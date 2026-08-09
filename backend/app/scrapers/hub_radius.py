"""Hub-city scrape radius and nested town/locality assignment.

Each configured hub (e.g. Galway) scrapes venues within a max radius (150 miles)
and labels deals for display as ``Galway - Tuam``, ``Galway - Galway City``, etc.
"""

from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

HUB_RADIUS_MILES = 150
HUB_RADIUS_M = int(HUB_RADIUS_MILES * 1609.344)  # ~241,402 m

# Within this distance of hub centre → "Galway City" (not a satellite town).
HUB_CENTRE_KM = 10.0
# Max distance to accept a satellite town label.
SATELLITE_MAX_KM = 85.0

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "hub_localities.json"
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 14  # 2 weeks

_OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

# Known satellite towns (lat/lon) merged with OSM discovery — ensures Tuam, Athenry, etc.
HUB_SATELLITE_SEEDS: dict[tuple[str, str], list[dict[str, float | str]]] = {
    ("IE", "Galway"): [
        {"name": "Tuam", "lat": 53.5139, "lon": -8.8569, "place": "town"},
        {"name": "Athenry", "lat": 53.2964, "lon": -8.7444, "place": "town"},
        {"name": "Ballinasloe", "lat": 53.3284, "lon": -8.2197, "place": "town"},
        {"name": "Loughrea", "lat": 53.1969, "lon": -8.5669, "place": "town"},
        {"name": "Clifden", "lat": 53.4891, "lon": -10.0214, "place": "town"},
        {"name": "Gort", "lat": 53.0664, "lon": -8.8189, "place": "town"},
        {"name": "Oranmore", "lat": 53.2683, "lon": -8.9200, "place": "town"},
        {"name": "Moycullen", "lat": 53.3389, "lon": -9.1814, "place": "village"},
    ],
    ("IE", "Dublin"): [
        {"name": "Bray", "lat": 53.2028, "lon": -6.1089, "place": "town"},
        {"name": "Swords", "lat": 53.4597, "lon": -6.2181, "place": "town"},
        {"name": "Dún Laoghaire", "lat": 53.2939, "lon": -6.1359, "place": "town"},
        {"name": "Naas", "lat": 53.2159, "lon": -6.6661, "place": "town"},
        {"name": "Maynooth", "lat": 53.3858, "lon": -6.5936, "place": "town"},
    ],
    ("IE", "Cork"): [
        {"name": "Cobh", "lat": 51.8503, "lon": -8.2943, "place": "town"},
        {"name": "Midleton", "lat": 51.9154, "lon": -8.1744, "place": "town"},
        {"name": "Mallow", "lat": 52.1338, "lon": -8.6419, "place": "town"},
    ],
    ("GB", "London"): [
        {"name": "Croydon", "lat": 51.3762, "lon": -0.0982, "place": "town"},
        {"name": "Watford", "lat": 51.6565, "lon": -0.3903, "place": "town"},
        {"name": "Slough", "lat": 51.5105, "lon": -0.5950, "place": "town"},
        {"name": "Reading", "lat": 51.4543, "lon": -0.9781, "place": "town"},
    ],
}

_PLACE_TYPE_RANK = {
    "hamlet": 0,
    "village": 1,
    "town": 2,
    "suburb": 3,
    "city": 4,
}


def hub_default_locality(hub: str) -> str:
    """Display label when venue sits at the hub centre (not a satellite town)."""
    name = (hub or "").strip().title()
    if not name:
        return "City Centre"
    if name.lower().endswith(" city"):
        return name
    return f"{name} City"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _load_cache() -> dict[str, Any]:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _cache_key(country: str, hub: str) -> str:
    return f"{country.strip().upper()}:{hub.strip().title()}"


def _is_hub_name(name: str, hub_title: str) -> bool:
    n = (name or "").strip().lower()
    h = hub_title.strip().lower()
    if not n or not h:
        return False
    if n == h:
        return True
    if n == f"{h} city":
        return True
    if hub_default_locality(h).lower() == n:
        return True
    return False


def _locality_from_tags(tags: dict[str, str], *, hub_title: str) -> str | None:
    """Prefer satellite town/village tags over the hub city name."""
    # Town/village/hamlet/suburb before city — avoids labelling Tuam venues as "Galway".
    ordered_keys = (
        "addr:town",
        "addr:village",
        "addr:hamlet",
        "addr:suburb",
        "addr:place",
        "addr:city",
    )
    hub_city: str | None = None
    for key in ordered_keys:
        raw = (tags.get(key) or "").strip()
        if not raw or len(raw) < 2:
            continue
        title = raw.title()
        if key == "addr:city" and _is_hub_name(title, hub_title):
            hub_city = title
            continue
        if not _is_hub_name(title, hub_title):
            return title
    return hub_city


def _element_coords(element: dict[str, Any]) -> tuple[float, float] | None:
    if element.get("type") == "node":
        lat, lon = element.get("lat"), element.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    center = element.get("center")
    if isinstance(center, dict):
        lat, lon = center.get("lat"), center.get("lon")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    return None


def _place_rank(place: dict[str, Any]) -> int:
    return _PLACE_TYPE_RANK.get(str(place.get("place") or "").lower(), 3)


def assign_locality(
    *,
    hub: str,
    lat: float | None,
    lon: float | None,
    localities: list[dict[str, Any]],
    tags: dict[str, str] | None = None,
) -> str:
    """Pick nested town label for a venue within a hub scrape."""
    hub_title = hub.strip().title()

    if tags:
        from_tags = _locality_from_tags(tags, hub_title=hub_title)
        if from_tags and not _is_hub_name(from_tags, hub_title):
            return from_tags

    if lat is None or lon is None or not localities:
        return hub_default_locality(hub_title)

    hub_place = next(
        (p for p in localities if _is_hub_name(str(p.get("name", "")), hub_title)),
        None,
    )
    hub_dist = (
        haversine_km(lat, lon, float(hub_place["lat"]), float(hub_place["lon"]))
        if hub_place
        else float("inf")
    )

    if hub_dist <= HUB_CENTRE_KM:
        return hub_default_locality(hub_title)

    ranked: list[tuple[float, int, dict[str, Any]]] = []
    for place in localities:
        plat = place.get("lat")
        plon = place.get("lon")
        pname = place.get("name")
        if plat is None or plon is None or not pname:
            continue
        dist = haversine_km(lat, lon, float(plat), float(plon))
        ranked.append((dist, _place_rank(place), place))
    ranked.sort(key=lambda row: (row[0], row[1]))

    # Nearest non-hub town/village within satellite range.
    for dist, _rank, place in ranked:
        pname = str(place.get("name", "")).strip().title()
        if not pname or _is_hub_name(pname, hub_title):
            continue
        if dist <= SATELLITE_MAX_KM:
            return pname

    if ranked:
        _dist, _rank, nearest = ranked[0]
        pname = str(nearest.get("name", "")).strip().title()
        if pname and not _is_hub_name(pname, hub_title):
            return pname

    return hub_default_locality(hub_title)


async def _fetch_places(lat: float, lon: float) -> list[dict[str, Any]]:
    query = f"""
[out:json][timeout:60];
(
  node["place"~"city|town|village|suburb|hamlet"](around:{HUB_RADIUS_M},{lat},{lon});
  way["place"~"city|town|village|suburb|hamlet"](around:{HUB_RADIUS_M},{lat},{lon});
);
out center tags 500;
""".strip()

    payload: dict[str, Any] = {"elements": []}
    async with httpx.AsyncClient(timeout=65.0) as client:
        for endpoint in _OVERPASS_ENDPOINTS:
            try:
                response = await client.post(endpoint, data={"data": query})
                response.raise_for_status()
                payload = response.json()
                break
            except Exception as exc:  # noqa: BLE001
                logger.info("Hub locality Overpass failed via %s: %s", endpoint, exc)

    places: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in payload.get("elements") or []:
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        name = str(tags.get("name") or "").strip()
        coords = _element_coords(element)
        if not name or not coords:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        places.append(
            {
                "name": name.title(),
                "lat": coords[0],
                "lon": coords[1],
                "place": str(tags.get("place") or ""),
            }
        )
    return places


def _merge_satellite_seeds(
    country_code: str,
    hub_city: str,
    places: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    key = (country_code.strip().upper(), hub_city.strip().title())
    seeds = HUB_SATELLITE_SEEDS.get(key, [])
    if not seeds:
        return places
    seen = {str(p.get("name", "")).lower() for p in places}
    merged = list(places)
    for seed in seeds:
        name = str(seed["name"]).title()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        merged.append(
            {
                "name": name,
                "lat": float(seed["lat"]),
                "lon": float(seed["lon"]),
                "place": str(seed.get("place") or "town"),
            }
        )
    return merged


async def discover_hub_localities(
    country_code: str,
    hub_city: str,
    *,
    lat: float,
    lon: float,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Towns/villages within HUB_RADIUS_MILES of a hub (cached)."""
    key = _cache_key(country_code, hub_city)
    cache = _load_cache()
    entry = cache.get(key) if isinstance(cache.get(key), dict) else None
    now = time.time()
    if (
        not force_refresh
        and entry
        and isinstance(entry.get("fetched_at"), (int, float))
        and now - float(entry["fetched_at"]) < _CACHE_TTL_SECONDS
        and isinstance(entry.get("places"), list)
    ):
        return _merge_satellite_seeds(country_code, hub_city, list(entry["places"]))

    places = await _fetch_places(lat, lon)
    places = _merge_satellite_seeds(country_code, hub_city, places)
    hub_title = hub_city.strip().title()
    if not any(_is_hub_name(str(p.get("name", "")), hub_title) for p in places):
        places.insert(
            0, {"name": hub_title, "lat": lat, "lon": lon, "place": "city"}
        )

    cache[key] = {
        "fetched_at": now,
        "lat": lat,
        "lon": lon,
        "radius_miles": HUB_RADIUS_MILES,
        "places": places,
    }
    try:
        _save_cache(cache)
    except OSError as exc:
        logger.info("Could not persist hub locality cache: %s", exc)

    logger.info(
        "Hub localities %s / %s: %d places within %smi",
        hub_title,
        country_code,
        len(places),
        HUB_RADIUS_MILES,
    )
    return places
