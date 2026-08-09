"""City-local independent ("mom and pop") venue discovery via OpenStreetMap.

Chains in hospitality packs are not enough for world-leading deal coverage.
For each scrape city we discover nearby F&B venues that publish a website,
prefer independents, map them into MealDeals venue categories, and cache
results so worldwide runs stay within Overpass rate limits.

Never invent merchants — only emit OSM (or cache) rows with a real name + URL.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "local_venues.json"
_OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

from app.scrapers.hub_radius import (
    HUB_SATELLITE_SEEDS,
    SATELLITE_MAX_KM,
    assign_locality,
    discover_hub_localities,
    haversine_km,
    hub_default_locality,
)

# Hub scrape: venues within 150 miles; cap per hub keeps zone jobs bite-sized.
_MAX_PER_HUB = 48
_MAX_PER_CATEGORY = 8
_MAX_PER_LOCALITY = 8
_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week
# Bump when hub/town assignment logic changes so cached sources re-label.
_LOCALITY_VERSION = 4
# Sample venues around hub centre + satellite towns (not one 150mi flood).
_HUB_SAMPLE_RADIUS_M = 12_000
_TOWN_SAMPLE_RADIUS_M = 8_000
_MAX_SATELLITE_SAMPLES = 8

# Name tokens that usually indicate global/national chains (prefer independents).
_CHAIN_NAME_RE = re.compile(
    r"(?i)\b("
    r"mcdonald|burger\s*king|kfc|subway|domino|pizza\s*hut|papa\s*john|"
    r"starbucks|costa|nandos|nando.?s|pret|greggs|wetherspoon|"
    r"marriott|hilton|holiday\s*inn|premier\s*inn|ibis|novotel|"
    r"tesco|sainsbury|aldi|lidl|walmart|carrefour|dunnes|supervalu|"
    r"centra|asda|morrisons|waitrose|chipotle|taco\s*bell|wendy|"
    r"hard\s*rock|olive\s*garden|applebee|ihop|pizza\s*express|"
    r"five\s*guys|tim\s*horton|dunkin"
    r")\b"
)

_AMENITY_TO_CATEGORY: dict[str, str] = {
    "restaurant": "Restaurants, Cafe's & Bistro's",
    "cafe": "Restaurants, Cafe's & Bistro's",
    "biergarten": "Clubs, Bars & Pubs",
    "pub": "Clubs, Bars & Pubs",
    "bar": "Clubs, Bars & Pubs",
    "nightclub": "Clubs, Bars & Pubs",
    "fast_food": "Food Trucks & Takeaway's",
    "food_court": "Food Trucks & Takeaway's",
    "ice_cream": "Restaurants, Cafe's & Bistro's",
    "hotel": "Hotels, Resorts & B&B's",
}

_TOURISM_TO_CATEGORY: dict[str, str] = {
    "hotel": "Hotels, Resorts & B&B's",
    "guest_house": "Hotels, Resorts & B&B's",
    "hostel": "Hotels, Resorts & B&B's",
    "motel": "Hotels, Resorts & B&B's",
    "apartment": "Hotels, Resorts & B&B's",
}


def _normalize_city_key(country: str, city: str) -> str:
    return f"{country.strip().upper()}:{(city or '').strip()}"


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


def _website_from_tags(tags: dict[str, str]) -> str | None:
    for key in ("website", "contact:website", "url", "contact:url"):
        raw = (tags.get(key) or "").strip()
        if not raw:
            continue
        if not raw.startswith(("http://", "https://")):
            raw = "https://" + raw
        parsed = urlparse(raw)
        if parsed.netloc and "." in parsed.netloc:
            return raw.split("#")[0].rstrip("/")
    return None


def _category_from_tags(tags: dict[str, str]) -> str | None:
    amenity = (tags.get("amenity") or "").strip().lower()
    if amenity in _AMENITY_TO_CATEGORY:
        return _AMENITY_TO_CATEGORY[amenity]
    tourism = (tags.get("tourism") or "").strip().lower()
    if tourism in _TOURISM_TO_CATEGORY:
        return _TOURISM_TO_CATEGORY[tourism]
    shop = (tags.get("shop") or "").strip().lower()
    if shop in {"convenience", "supermarket", "greengrocer", "deli", "bakery"}:
        return "Deli's and Grocers"
    craft = (tags.get("craft") or "").strip().lower()
    if craft == "winery" or "winery" in (tags.get("name") or "").lower():
        return "Wine Farms & Entertainment Venues"
    return None


def _is_likely_chain(name: str) -> bool:
    return bool(_CHAIN_NAME_RE.search(name or ""))


def _overpass_query(lat: float, lon: float, radius_m: int, *, limit: int) -> str:
    return f"""
[out:json][timeout:35];
(
  node["amenity"~"restaurant|cafe|pub|bar|fast_food|biergarten|nightclub|food_court|ice_cream"]["website"](around:{radius_m},{lat},{lon});
  way["amenity"~"restaurant|cafe|pub|bar|fast_food|biergarten|nightclub|food_court|ice_cream"]["website"](around:{radius_m},{lat},{lon});
  node["tourism"~"hotel|guest_house|hostel|motel"]["website"](around:{radius_m},{lat},{lon});
  way["tourism"~"hotel|guest_house|hostel|motel"]["website"](around:{radius_m},{lat},{lon});
  node["shop"~"convenience|supermarket|deli|bakery"]["website"](around:{radius_m},{lat},{lon});
  way["shop"~"convenience|supermarket|deli|bakery"]["website"](around:{radius_m},{lat},{lon});
  node["craft"="winery"]["website"](around:{radius_m},{lat},{lon});
  way["craft"="winery"]["website"](around:{radius_m},{lat},{lon});
);
out center tags {limit};
""".strip()


async def _fetch_overpass_around(
    lat: float, lon: float, *, radius_m: int, limit: int
) -> list[dict[str, Any]]:
    query = _overpass_query(lat, lon, radius_m, limit=limit)
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(2):
            for endpoint in _OVERPASS_ENDPOINTS:
                try:
                    response = await client.post(endpoint, data={"data": query})
                    response.raise_for_status()
                    payload = response.json()
                    return list(payload.get("elements") or [])
                except Exception as exc:  # noqa: BLE001 — fall through endpoints
                    last_exc = exc
                    logger.info("Overpass failed via %s: %s", endpoint, exc)
            if attempt == 0:
                await asyncio.sleep(1.5)
    if last_exc:
        logger.info("Local discovery skipped (Overpass unavailable): %s", last_exc)
    return []


def _sample_points(
    *,
    country: str,
    hub: str,
    hub_lat: float,
    hub_lon: float,
    localities: list[dict[str, Any]],
) -> list[tuple[str, float, float, int]]:
    """Hub centre + nearby towns to sample (label, lat, lon, radius_m)."""
    hub_title = hub.strip().title()
    points: list[tuple[str, float, float, int]] = [
        (hub_title, hub_lat, hub_lon, _HUB_SAMPLE_RADIUS_M)
    ]
    seen = {hub_title.lower()}

    # Curated seeds keep list order (Tuam before distant Clifden) so rate-limits
    # don't skip the towns we care most about.
    seed_key = (country.strip().upper(), hub_title)
    for seed in HUB_SATELLITE_SEEDS.get(seed_key, []):
        name = str(seed["name"]).title()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        points.append(
            (name, float(seed["lat"]), float(seed["lon"]), _TOWN_SAMPLE_RADIUS_M)
        )
        if len(points) - 1 >= _MAX_SATELLITE_SAMPLES:
            return points

    # Fill remaining slots from OSM towns nearest the hub.
    osm_candidates: list[tuple[float, str, float, float]] = []
    for place in localities:
        name = str(place.get("name") or "").strip().title()
        if not name or name.lower() in seen:
            continue
        plat, plon = place.get("lat"), place.get("lon")
        if plat is None or plon is None:
            continue
        ptype = str(place.get("place") or "").lower()
        if ptype not in {"town", "village", "suburb"}:
            continue
        dist = haversine_km(hub_lat, hub_lon, float(plat), float(plon))
        if dist > SATELLITE_MAX_KM or dist < 4.0:
            continue
        osm_candidates.append((dist, name, float(plat), float(plon)))
    osm_candidates.sort(key=lambda row: row[0])
    for _dist, name, plat, plon in osm_candidates:
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        points.append((name, plat, plon, _TOWN_SAMPLE_RADIUS_M))
        if len(points) - 1 >= _MAX_SATELLITE_SAMPLES:
            break
    return points


async def _fetch_overpass_for_hub(
    *,
    country: str,
    hub: str,
    lat: float,
    lon: float,
    localities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fetch venues around hub + satellite towns so Tuam/Athenry are not drowned out."""
    points = _sample_points(
        country=country, hub=hub, hub_lat=lat, hub_lon=lon, localities=localities
    )
    elements: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    per_point = max(12, _MAX_PER_LOCALITY * 3)
    for idx, (label, plat, plon, radius_m) in enumerate(points):
        if idx > 0:
            await asyncio.sleep(0.8)
        batch = await _fetch_overpass_around(
            plat, plon, radius_m=radius_m, limit=per_point
        )
        added = 0
        for element in batch:
            eid = f"{element.get('type')}:{element.get('id')}"
            if eid in seen_ids:
                continue
            seen_ids.add(eid)
            elements.append(element)
            added += 1
        logger.info(
            "Local Overpass %s / %s @ %s: %d elements",
            hub,
            country,
            label,
            added,
        )
    return elements


def _select_independents(
    elements: list[dict[str, Any]],
    *,
    hub: str,
    localities: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Dedupe, prefer non-chains, balance categories, return scrape sources."""
    by_category: dict[str, list[dict[str, str]]] = {}
    seen_urls: set[str] = set()
    seen_names: set[str] = set()

    independents: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []

    for element in elements:
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        str_tags = {str(k): str(v) for k, v in tags.items()}
        name = str(str_tags.get("name") or "").strip()
        website = _website_from_tags(str_tags)
        category = _category_from_tags(str_tags)
        if not name or not website or not category:
            continue
        name_key = name.lower()
        host = urlparse(website).netloc.lower()
        if name_key in seen_names or host in seen_urls:
            continue
        seen_names.add(name_key)
        seen_urls.add(host)
        coords = _element_coords(element)
        lat, lon = (coords[0], coords[1]) if coords else (None, None)
        area_local = assign_locality(
            hub=hub,
            lat=lat,
            lon=lon,
            localities=localities,
            tags=str_tags,
        )
        row = {
            "merchant": name[:120],
            "url": website[:500],
            "venue_category": category,
            "independent": not _is_likely_chain(name),
            "area_local": area_local,
        }
        if row["independent"]:
            independents.append(row)
        else:
            chains.append(row)

    # Round-robin across categories so pubs/takeaways/grocers are not crowded
    # out by the denser restaurant layer in OSM. Also cap per locality so
    # Galway City does not absorb the whole hub budget.
    pools: dict[str, list[dict[str, Any]]] = {}
    for row in independents + chains:
        pools.setdefault(row["venue_category"], []).append(row)

    priority = [
        "Clubs, Bars & Pubs",
        "Food Trucks & Takeaway's",
        "Deli's and Grocers",
        "Restaurants, Cafe's & Bistro's",
        "Hotels, Resorts & B&B's",
        "Wine Farms & Entertainment Venues",
    ]
    for category in list(pools):
        if category not in priority:
            priority.append(category)

    selected: list[dict[str, str]] = []
    by_category.clear()
    by_locality: dict[str, int] = {}
    progressed = True
    while progressed and len(selected) < _MAX_PER_HUB:
        progressed = False
        for category in priority:
            bucket = by_category.setdefault(category, [])
            if len(bucket) >= _MAX_PER_CATEGORY:
                continue
            pool = pools.get(category) or []
            if not pool:
                continue
            # Prefer under-represented localities within this category pool.
            pick_idx = None
            for idx, candidate in enumerate(pool):
                loc = str(candidate.get("area_local") or hub_default_locality(hub))
                if by_locality.get(loc, 0) < _MAX_PER_LOCALITY:
                    pick_idx = idx
                    break
            if pick_idx is None:
                continue
            row = pool.pop(pick_idx)
            loc = str(row.get("area_local") or hub_default_locality(hub))
            by_locality[loc] = by_locality.get(loc, 0) + 1
            bucket.append(row)
            selected.append(
                {
                    "merchant": row["merchant"],
                    "url": row["url"],
                    "venue_category": category,
                    "area_local": row.get("area_local"),
                    "source_kind": "local_independent"
                    if row["independent"]
                    else "local_chain",
                }
            )
            progressed = True
            if len(selected) >= _MAX_PER_HUB:
                break
    return selected


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


async def discover_local_venues(
    country_code: str,
    city: str,
    *,
    force_refresh: bool = False,
) -> list[dict[str, str]]:
    """Return city-local venue sources (cached OSM independents + locals)."""
    from app.services.ingest import CITY_COORDS

    country = country_code.strip().upper()
    city_name = (city or "").replace("-", " ").strip().title()
    cache_key = _normalize_city_key(country, city_name)
    cache = _load_cache()
    entry = cache.get(cache_key) if isinstance(cache.get(cache_key), dict) else None
    now = time.time()
    if (
        not force_refresh
        and entry
        and entry.get("locality_version") == _LOCALITY_VERSION
        and isinstance(entry.get("fetched_at"), (int, float))
        and now - float(entry["fetched_at"]) < _CACHE_TTL_SECONDS
        and isinstance(entry.get("sources"), list)
    ):
        return [dict(s) for s in entry["sources"] if isinstance(s, dict)]

    coords = CITY_COORDS.get((country, city_name))
    if not coords:
        # Try original casing from scrape path.
        coords = CITY_COORDS.get((country, (city or "").strip()))
    if not coords:
        logger.info("No CITY_COORDS for %s / %s — skip local discovery", country, city)
        return []

    lat, lon = coords
    localities = await discover_hub_localities(
        country, city_name, lat=lat, lon=lon, force_refresh=force_refresh
    )
    elements = await _fetch_overpass_for_hub(
        country=country,
        hub=city_name,
        lat=lat,
        lon=lon,
        localities=localities,
    )
    sources = _select_independents(elements, hub=city_name, localities=localities)
    cache[cache_key] = {
        "fetched_at": now,
        "locality_version": _LOCALITY_VERSION,
        "lat": lat,
        "lon": lon,
        "sources": sources,
    }
    try:
        _save_cache(cache)
    except OSError as exc:
        logger.info("Could not persist local venue cache: %s", exc)

    logger.info(
        "Local discovery %s / %s: %d venues (from %d OSM elements)",
        city_name,
        country,
        len(sources),
        len(elements),
    )
    return sources


def merge_local_sources(
    pack_sources: list[dict[str, str]],
    local_sources: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Append local independents after pack/chain sources (deduped by name)."""
    seen = {s["merchant"].strip().lower() for s in pack_sources if s.get("merchant")}
    merged = [dict(s) for s in pack_sources]
    for source in local_sources:
        name = (source.get("merchant") or "").strip()
        url = (source.get("url") or "").strip()
        if not name or not url:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        row = {"merchant": name, "url": url}
        if source.get("source_kind"):
            row["source_kind"] = str(source["source_kind"])
        if source.get("venue_category"):
            row["venue_category"] = str(source["venue_category"])
        if source.get("area_local"):
            row["area_local"] = str(source["area_local"])
        merged.append(row)
    return merged
