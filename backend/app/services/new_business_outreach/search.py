"""Classify restaurants, takeaways (including chippers), and public wine venues."""

from __future__ import annotations

import re

from app.services.new_business_outreach.constants import (
    RESTAURANTS,
    TAKEAWAYS,
    WINE_FARMS,
)
from app.services.new_business_outreach.tiles import OutreachTile
from app.services.new_business_outreach.types import VenueCandidate

ELEMENT_CAP = 50

_CHIPPER_NAME = re.compile(
    r"(?i)\b(?:chipper|chippy|fish\s*(?:and|&|\+)\s*chips?|chip\s*shop)\b"
)
_WINE_PUBLIC = re.compile(r"(?i)\b(?:cellar|tasting|vineyard|winery|wine\s*farm)\b")


def overpass_query(tile: OutreachTile) -> str:
    """One bounded query: restaurants, fast food, chippers, and wine venues."""
    bbox = f"{tile.south},{tile.west},{tile.north},{tile.east}"
    return f"""
[out:json][timeout:25];
(
  nwr["name"]["amenity"="restaurant"]({bbox});
  nwr["name"]["amenity"="fast_food"]({bbox});
  nwr["name"]["cuisine"~"fish_and_chips|fish_and_chip"]({bbox});
  nwr["name"]["craft"="winery"]({bbox});
  nwr["name"]["tourism"="winery"]({bbox});
  nwr["name"]["tourism"="wine_cellar"]({bbox});
  nwr["name"]["amenity"="winery"]({bbox});
  nwr["name"]["shop"="wine"]({bbox});
);
out center tags {ELEMENT_CAP};
""".strip()


def _blob(tags: dict[str, str]) -> str:
    return " ".join(
        tags.get(key, "")
        for key in ("name", "description", "tourism", "shop", "craft", "amenity")
    )


def is_public_wine(tags: dict[str, str]) -> bool:
    """Wineries, wine farms, and vineyards that have a cellar door or tasting room.

    A bare ``shop=wine`` in a city is a bottle shop, not a farm, so it is left out
    unless the name or tags also say cellar, tasting, vineyard, or winery.
    """
    craft = (tags.get("craft") or "").lower()
    tourism = (tags.get("tourism") or "").lower()
    amenity = (tags.get("amenity") or "").lower()
    shop = (tags.get("shop") or "").lower()
    landuse = (tags.get("landuse") or "").lower()
    if craft == "winery" or amenity == "winery" or tourism in {"winery", "wine_cellar"}:
        return True
    public = bool(_WINE_PUBLIC.search(_blob(tags)))
    if landuse == "vineyard" and (shop == "wine" or tourism == "wine_cellar" or public):
        return True
    if shop == "wine" and public:
        return True
    return False


def is_chipper(tags: dict[str, str]) -> bool:
    cuisine = (tags.get("cuisine") or "").lower().replace(" ", "_")
    if "fish_and_chip" in cuisine:
        return True
    return _CHIPPER_NAME.search(tags.get("name") or "") is not None


def venue_category(tags: dict[str, str]) -> str | None:
    """Parent category, or None when the element is outside this scrape."""
    amenity = (tags.get("amenity") or "").lower()
    if is_public_wine(tags):
        return WINE_FARMS
    if amenity == "fast_food" or is_chipper(tags):
        return TAKEAWAYS
    if amenity == "restaurant":
        return RESTAURANTS
    return None


def _website(tags: dict[str, str]) -> str | None:
    for key in ("contact:website", "website", "contact:url", "url"):
        raw = (tags.get(key) or "").strip()
        if raw.startswith(("http://", "https://")):
            return raw.split()[0][:500]
    return None


def _emails(tags: dict[str, str]) -> tuple[str, ...]:
    raw = (tags.get("contact:email") or tags.get("email") or "").replace("mailto:", "")
    found: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[;,\s]+", raw):
        email = part.strip().strip(".").lower()
        if "@" not in email or email in seen:
            continue
        seen.add(email)
        found.append(email)
    return tuple(found)


def _address(tags: dict[str, str]) -> str | None:
    parts = [
        (tags.get(key) or "").strip()
        for key in ("addr:housenumber", "addr:street", "addr:city", "addr:postcode")
    ]
    text = ", ".join(part for part in parts if part)
    return text[:255] or None


def _city(tags: dict[str, str], tile: OutreachTile) -> str:
    for key in ("addr:city", "addr:town", "addr:village", "addr:suburb"):
        value = (tags.get(key) or "").strip()
        if value:
            return value[:120]
    return tile.name[:120]


def _country(tags: dict[str, str], tile: OutreachTile) -> str:
    code = (tags.get("addr:country") or "").strip().upper()
    if len(code) == 2 and code.isalpha():
        return code
    return tile.country_code


def candidates_from_elements(
    elements: list[dict],
    tile: OutreachTile,
) -> list[VenueCandidate]:
    """Map one Overpass payload into in-scope venues. Chains are filtered later."""
    found: list[VenueCandidate] = []
    seen: set[tuple[str, str]] = set()
    for element in elements:
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        str_tags = {str(key): str(value) for key, value in tags.items()}
        name = (str_tags.get("name") or "").strip()
        category = venue_category(str_tags)
        if not name or category is None:
            continue
        website = _website(str_tags)
        emails = _emails(str_tags)
        dedupe = (name.lower(), (website or (emails[0] if emails else "")).lower())
        if dedupe in seen:
            continue
        seen.add(dedupe)
        found.append(
            VenueCandidate(
                business_name=name[:255],
                country_code=_country(str_tags, tile),
                city=_city(str_tags, tile),
                venue_category=category,
                zone_id=tile.lead_zone,
                website=website,
                emails=emails,
                phone=((str_tags.get("contact:phone") or str_tags.get("phone") or "")[:64] or None),
                osm_brand=(str_tags.get("brand") or "").strip() or None,
                osm_brand_wikidata=(str_tags.get("brand:wikidata") or "").strip() or None,
                operator=(str_tags.get("operator") or "").strip() or None,
                address=_address(str_tags),
                tile_id=tile.tile_id,
                lead_source="osm" if emails else None,
            )
        )
    return found
