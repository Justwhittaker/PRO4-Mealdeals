"""Chain and group heuristics for Fishy Finger Sub.

Fishy Finger Sub looks for independent small and medium hospitality businesses.
A venue is skipped when any heuristic below matches. Thresholds are deliberate
so a single local café is kept and a brand that shows up across the run is not.

Heuristics
----------
known_chain
    The business name, OSM ``brand``, or OSM ``operator`` matches the deal
    scraper's national-chain list (``app.scrapers.source_filters``) or the
    extra group/franchise list in this module (hotel groups, pubcos, QSR).

group_name
    The name itself says it is a group: "restaurant group", "hospitality
    group", "pub group", or "hotel group".

brand_wikidata
    OpenStreetMap ``brand:wikidata`` is set. That tag points at a branded
    chain, not a one-off venue.

franchise_page
    The website path, or the homepage text when we fetched it, looks like a
    locations directory or a franchise pitch (``/locations``, ``/franchising``,
    "our locations", "franchise opportunities", "find a restaurant").

multi_city_brand
    The same normalized brand (punctuation and legal suffixes removed) appears
    in ``BRAND_CITY_THRESHOLD`` or more distinct cities. The count includes
    this run and businesses already stored (marketing contacts and merchants
    that already have a deal). A name that only exists in one city is not
    treated as a chain on this rule.

shared_corporate_domain
    One registrable domain (``oak.example`` and ``www.oak.example`` count as
    the same host) is used by ``DOMAIN_VENUE_THRESHOLD`` or more different
    venue names, again including venues already stored. Social and
    website-builder hosts (Facebook, Instagram, Linktree, Wix, Squarespace,
    and similar) are ignored here, because many independents share those
    platforms without being one company.

A venue that matches none of these is eligible to continue to the email check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.scrapers.source_filters import is_national_chain

# Same brand in this many cities (this run) is treated as a chain or group.
BRAND_CITY_THRESHOLD = 3
# Distinct venue names on one registrable domain.
DOMAIN_VENUE_THRESHOLD = 4

# Brands the deal-scraper regex does not already cover.
_EXTRA_CHAIN_RE = re.compile(
    r"(?i)\b("
    r"hyatt|radisson|sheraton|westin|accor|travelodge|best\s*western|"
    r"four\s*seasons|intercontinental|crowne\s*plaza|citizenm|motel\s*one|"
    r"wagamama|pizza\s*express|greene\s*king|hungry\s*horse|all\s*bar\s*one|"
    r"slug\s*(?:and|&)\s*lettuce|chef\s*(?:and|&)\s*brewer|beefeater|"
    r"harvester|toby\s*carvery|wagamama|nandos|cafe\s*nero|caffe\s*nero|"
    r"coffee\s*club|gloria\s*jean|tim\s*hortons|dunkin|five\s*guys|"
    r"taco\s*bell|wendys|wendy.?s|kfc|subway|domino.?s|pizza\s*hut"
    r")\b"
)

_GROUP_NAME_RE = re.compile(
    r"(?i)\b(?:restaurant|hospitality|pub|hotel)\s+group\b"
)

_FRANCHISE_PATH_RE = re.compile(
    r"(?i)/(?:locations|our-locations|all-locations|find-a-restaurant|"
    r"find-a-store|store-locator|restaurant-locator|franchis(?:e|ing)|"
    r"our-restaurants|our-pubs|our-cafes)(?:/|$)"
)

_FRANCHISE_TEXT_RE = re.compile(
    r"(?i)franchise opportunit|own a franchise|become a franchisee|"
    r"find a (?:restaurant|store|location)|locations near you|"
    r"our locations|view all locations|restaurant locator"
)

_LEGAL_SUFFIX_RE = re.compile(
    r"\b(?:ltd|limited|llc|inc|incorporated|pty|gmbh|plc|co|company)\b",
    re.I,
)

# Hosts shared by many independents. Not evidence of one corporate group.
_SHARED_PLATFORM_SUFFIXES: frozenset[str] = frozenset(
    {
        "facebook.com",
        "fb.com",
        "instagram.com",
        "linktr.ee",
        "linktree.com",
        "wix.com",
        "wixsite.com",
        "squarespace.com",
        "square.site",
        "squareup.com",
        "godaddysites.com",
        "wordpress.com",
        "weebly.com",
        "carrd.co",
        "github.io",
        "sites.google.com",
        "business.site",
        "tumblr.com",
        "myshopify.com",
        "shopify.com",
        "toasttab.com",
        "opentable.com",
        "resy.com",
        "thefork.com",
    }
)

_MULTI_PART_SUFFIXES: tuple[str, ...] = (
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "com.br",
    "co.za",
    "com.mx",
    "co.jp",
    "com.sg",
    "co.il",
    "com.tr",
    "com.ar",
    "co.kr",
    "com.hk",
)


@dataclass(frozen=True)
class ChainSignals:
    """Inputs the chain check needs beyond the venue's own name and URL."""

    brand_city_count: int = 1
    domain_venue_count: int = 1


def brand_key(name: str | None) -> str:
    """Normalize a venue or brand name so city copies compare equal."""
    text = (name or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = _LEGAL_SUFFIX_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.startswith("the "):
        text = text[4:]
    return text


def website_host(url: str | None) -> str | None:
    if not url:
        return None
    raw = url.strip()
    if raw and not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    try:
        host = urlparse(raw).hostname or ""
    except ValueError:
        return None
    host = host.lower().removeprefix("www.")
    return host or None


def is_shared_platform_host(host: str | None) -> bool:
    """True for social profiles and website builders, not a group's own domain."""
    if not host:
        return False
    host = host.lower().removeprefix("www.")
    for suffix in _SHARED_PLATFORM_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def registrable_domain(host: str | None) -> str | None:
    """Registrable host: ``mail.oak.co.uk`` and ``oak.co.uk`` share a key."""
    if not host:
        return None
    host = host.lower().strip(".").removeprefix("www.")
    labels = [part for part in host.split(".") if part]
    if len(labels) < 2:
        return host or None
    for suffix in _MULTI_PART_SUFFIXES:
        if host == suffix:
            return host
        if host.endswith("." + suffix):
            extra = host[: -(len(suffix) + 1)].split(".")
            if not extra:
                return host
            return f"{extra[-1]}.{suffix}"
    return ".".join(labels[-2:])


def corporate_domain(url: str | None) -> str | None:
    """Domain used for the shared-domain rule, or None when it should not count."""
    host = website_host(url)
    if not host or is_shared_platform_host(host):
        return None
    return registrable_domain(host)


def _looks_like_known_chain(*names: str | None) -> bool:
    for name in names:
        text = (name or "").strip()
        if not text:
            continue
        # Empty source kind so the name regex runs. ``local_independent`` would
        # suppress it, which is the wrong signal for this lead list.
        if is_national_chain(text, {}):
            return True
        if _EXTRA_CHAIN_RE.search(text):
            return True
    return False


def _franchise_hit(website: str | None, page_text: str | None) -> bool:
    if website:
        raw = website.strip()
        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"
        try:
            path = urlparse(raw).path or ""
        except ValueError:
            path = ""
        if _FRANCHISE_PATH_RE.search(path):
            return True
    if page_text and _FRANCHISE_TEXT_RE.search(page_text):
        return True
    return False


def chain_exclusion_reason(
    *,
    business_name: str,
    website: str | None = None,
    page_text: str | None = None,
    osm_brand: str | None = None,
    osm_brand_wikidata: str | None = None,
    operator: str | None = None,
    signals: ChainSignals | None = None,
) -> str | None:
    """Return a heuristic id when the venue should be skipped, else None.

    See the module docstring for what each id means.
    """
    flags = signals or ChainSignals()
    if _looks_like_known_chain(business_name, osm_brand, operator):
        return "known_chain"
    if _GROUP_NAME_RE.search(business_name or "") or _GROUP_NAME_RE.search(osm_brand or ""):
        return "group_name"
    if (osm_brand_wikidata or "").strip():
        return "brand_wikidata"
    if _franchise_hit(website, page_text):
        return "franchise_page"
    key = brand_key(osm_brand or business_name)
    if key and flags.brand_city_count >= BRAND_CITY_THRESHOLD:
        return "multi_city_brand"
    if corporate_domain(website) and flags.domain_venue_count >= DOMAIN_VENUE_THRESHOLD:
        return "shared_corporate_domain"
    return None
