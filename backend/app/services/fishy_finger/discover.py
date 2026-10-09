"""Turn OpenStreetMap hub samples into Fishy Finger Sub candidates.

Uses the same Overpass sample as deal discovery (``fetch_hub_osm_elements``),
including the winery pass on wine hubs. It does not read or write the deal
scraper venue cache, so a lead run cannot refresh or poison deal sources.
"""

from __future__ import annotations

import ipaddress
import logging
import re
from urllib.parse import urlparse

import httpx

from app.core.task_errors import reraise_if_fatal
from app.scrapers.local_discovery import fetch_hub_osm_elements, osm_contact_from_element
from app.scrapers.politeness import pace_host_sync
from app.services.fishy_finger.types import VenueCandidate

logger = logging.getLogger(__name__)

_EMAIL_FIND = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_USER_AGENT = "DineADeal/1.0 (+https://dineadeal.com; hospitality lead discovery)"
_HOMEPAGE_BYTES = 200_000


def emails_from_html(html: str) -> tuple[str, ...]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _EMAIL_FIND.findall(html or ""):
        email = match.strip().strip(".").lower()
        if email in seen:
            continue
        seen.add(email)
        found.append(email)
    return tuple(found)


def _public_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." in host
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
    )


def fetch_homepage(url: str) -> tuple[str, str] | None:
    """GET a venue homepage. None when the URL is unsafe or the request fails."""
    if not _public_http_url(url):
        return None
    pace_host_sync(url)
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": _USER_AGENT})
    except Exception as exc:  # noqa: BLE001 — one dead site must not abort the zone
        reraise_if_fatal(exc)
        logger.info("Fishy homepage skipped for %s: %s", url, exc)
        return None
    if response.status_code >= 400:
        return None
    final = str(response.url)
    if not _public_http_url(final):
        return None
    return final, response.text[:_HOMEPAGE_BYTES]


def candidates_from_osm_elements(
    elements: list[dict],
    *,
    country_code: str,
    city: str,
    zone_id: str,
) -> list[VenueCandidate]:
    """Map Overpass elements into lead candidates. Chains are filtered later."""
    found: list[VenueCandidate] = []
    seen: set[tuple[str, str]] = set()
    for element in elements:
        contact = osm_contact_from_element(element)
        if contact is None:
            continue
        name = contact["merchant"]
        website = contact.get("url") or None
        emails = tuple(contact.get("emails") or ())
        dedupe = (name.lower(), (website or emails[0] if emails else "").lower())
        if dedupe in seen:
            continue
        seen.add(dedupe)
        found.append(
            VenueCandidate(
                business_name=name,
                country_code=country_code,
                city=city,
                venue_category=contact["venue_category"],
                zone_id=zone_id,
                website=website,
                emails=emails,
                phone=contact.get("phone") or None,
                osm_brand=contact.get("brand") or None,
                osm_brand_wikidata=contact.get("brand_wikidata") or None,
                operator=contact.get("operator") or None,
            )
        )
    return found


async def discover_fishy_candidates(
    country_code: str,
    city: str,
    zone_id: str,
) -> list[VenueCandidate]:
    """OSM candidates for one hub. Empty when the city has no coordinates."""
    elements = await fetch_hub_osm_elements(country_code, city)
    return candidates_from_osm_elements(
        elements,
        country_code=country_code,
        city=city,
        zone_id=zone_id,
    )
