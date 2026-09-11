"""Affiliate URL cleaning and wrapping for regional networks."""

from __future__ import annotations

from enum import Enum
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse, urlunparse

from app.core.config import Settings, get_settings

# Common tracking / analytics query params to strip for clean_url
_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "gclid",
        "fbclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_",
        "affiliate",
        "aff",
        "tag",
        "ascsubtag",
        "campid",
        "creative",
        "adgroupid",
        "device",
        "gclsrc",
        "dclid",
        "yclid",
        "wickedid",
        "twclid",
        "igshid",
        "si",
        "spm",
        "scm",
    }
)

# Params scrapers add so the same chain can exist in multiple cities.
# They must never be sent on click-through — merchants 404 or ignore them.
_IDENTITY_PARAMS = frozenset(
    {
        "city",
        "locality",
        "country",
        "md_city",
        "md_locality",
        "md_country",
    }
)
_SCRAPER_UTM_SOURCE = "mealdeals_scraper"


class AffiliateNetwork(str, Enum):
    AMAZON = "amazon"
    BOOKING = "booking"
    AWIN = "awin"
    CJ = "cj"
    IMPACT = "impact"
    RAKUTEN = "rakuten"
    UNKNOWN = "unknown"


def _rebuild(
    parsed: ParseResult,
    *,
    query: str | None = None,
    fragment: str | None = None,
) -> str:
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query if query is None else query,
            parsed.fragment if fragment is None else fragment,
        )
    )


def _query_looks_like_scrape_identity(query: str) -> bool:
    """True when query (or a fragment leftover) carries scraper uniqueness params."""
    lower = (query or "").lower()
    if "utm_source=mealdeals_scraper" in lower:
        return True
    keys = {key.lower() for key, _ in parse_qsl(query, keep_blank_values=True)}
    if {"city", "locality", "country"}.issubset(keys):
        return True
    if keys & {"md_city", "md_locality", "md_country"}:
        return True
    # Malformed concat: id=1?city=London&locality=X&country=GB
    if "city=" in lower and "locality=" in lower and "country=" in lower:
        return True
    return False


def repair_concatenated_url(url: str) -> str:
    """
    Fix uniqueness params that were string-concatenated with a second '?'
    or appended after a '#' fragment (hash-router deal links).
    """
    if not url or not url.strip():
        return url
    parsed = urlparse(url.strip())
    fragment = parsed.fragment or ""
    query = parsed.query or ""

    # https://merchant.com/order/#!/deals?city=London&locality=...
    if "?" in fragment:
        frag_path, frag_query = fragment.split("?", 1)
        if _query_looks_like_scrape_identity(frag_query):
            fragment = frag_path
            query = f"{query}&{frag_query}" if query else frag_query

    # https://merchant.com/offers?promo=1?city=London&locality=...
    if "?" in query:
        before, after = query.split("?", 1)
        if _query_looks_like_scrape_identity(after):
            query = f"{before}&{after}" if before else after

    return _rebuild(parsed, query=query, fragment=fragment)


def append_query_params(url: str, extra: dict[str, str]) -> str:
    """Merge query params without destroying an existing query string or fragment."""
    repaired = repair_concatenated_url(url)
    parsed = urlparse(repaired)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in extra.items():
        if value is None:
            continue
        params[key] = value
    return _rebuild(parsed, query=urlencode(params), fragment=parsed.fragment)


def with_scrape_identity(
    url: str,
    *,
    city: str,
    locality: str,
    country: str,
) -> str:
    """Attach per-area identity params used for ingest uniqueness, not click-through."""
    return append_query_params(
        url,
        {
            "city": city,
            "locality": locality,
            "country": country,
            "utm_source": _SCRAPER_UTM_SOURCE,
        },
    )


def strip_tracking_params(url: str) -> str:
    """Return a clean URL with common tracking query parameters removed."""
    repaired = repair_concatenated_url(url)
    parsed = urlparse(repaired)
    filtered = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key.lower() not in _TRACKING_PARAMS
    ]
    return _rebuild(parsed, query=urlencode(filtered), fragment=parsed.fragment)


def _should_strip_identity(pairs: list[tuple[str, str]]) -> bool:
    keys = {key.lower() for key, _ in pairs}
    if {"city", "locality", "country"}.issubset(keys):
        return True
    if keys & {"md_city", "md_locality", "md_country"}:
        return True
    return any(
        key.lower() == "utm_source" and value == _SCRAPER_UTM_SOURCE
        for key, value in pairs
    )


def outbound_destination_url(url: str) -> str:
    """
    Merchant offer URL a visitor should open.

    Strips scraper identity params (city/locality/country) and tracking tags,
    preserves path + hash-router fragments, and repairs malformed concatenations.
    """
    if not url or not str(url).strip():
        return url
    repaired = repair_concatenated_url(url.strip())
    parsed = urlparse(repaired)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    strip_identity = _should_strip_identity(pairs)
    filtered: list[tuple[str, str]] = []
    for key, value in pairs:
        lower = key.lower()
        if lower in _TRACKING_PARAMS:
            continue
        if strip_identity and lower in _IDENTITY_PARAMS:
            continue
        filtered.append((key, value))
    return _rebuild(parsed, query=urlencode(filtered), fragment=parsed.fragment)


def detect_network(url: str) -> AffiliateNetwork:
    host = urlparse(url).netloc.lower()
    if "amazon." in host or host.startswith("amzn."):
        return AffiliateNetwork.AMAZON
    if "booking.com" in host:
        return AffiliateNetwork.BOOKING
    if "awin1.com" in host or "awin.com" in host:
        return AffiliateNetwork.AWIN
    if "anrdoezrs.net" in host or "jdoqocy.com" in host or "tkqlhce.com" in host:
        return AffiliateNetwork.CJ
    if "impact.com" in host or "impactradius" in host:
        return AffiliateNetwork.IMPACT
    if "rakuten" in host or "linksynergy.com" in host:
        return AffiliateNetwork.RAKUTEN
    return AffiliateNetwork.UNKNOWN


def wrap_affiliate_url(
    url: str,
    *,
    network: AffiliateNetwork | None = None,
    settings: Settings | None = None,
) -> str:
    """
    Wrap a destination URL with the appropriate regional affiliate tags.

    Tags are read from environment-backed Settings so each deploy region can
    use different publisher IDs without code changes.
    """
    cfg = settings or get_settings()
    clean = outbound_destination_url(url)
    net = network or detect_network(clean)
    parsed = urlparse(clean)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    if net is AffiliateNetwork.AMAZON:
        params["tag"] = cfg.amazon_associate_tag
    elif net is AffiliateNetwork.BOOKING:
        params["aid"] = cfg.booking_aid
    elif net is AffiliateNetwork.AWIN:
        # Awin click-through wrapper when given a merchant deep link
        if "awin1.com" not in parsed.netloc.lower():
            encoded = urlencode({"ued": clean, "awinaffid": cfg.awin_publisher_id})
            return f"https://www.awin1.com/cread.php?{encoded}"
        params["awinaffid"] = cfg.awin_publisher_id
    elif net is AffiliateNetwork.CJ:
        params["sid"] = cfg.cj_website_id
    elif net is AffiliateNetwork.IMPACT:
        params["irpid"] = cfg.impact_campaign_id
    elif net is AffiliateNetwork.RAKUTEN:
        params["mid"] = cfg.rakuten_mid
    elif net is AffiliateNetwork.UNKNOWN:
        pass
    else:
        # Exhaustive check for newly added enum members
        never: AffiliateNetwork = net
        raise ValueError(f"Unhandled affiliate network: {never}")

    new_query = urlencode(params)
    return _rebuild(parsed, query=new_query, fragment=parsed.fragment)


def build_affiliate_urls(raw_url: str, settings: Settings | None = None) -> tuple[str, str]:
    """Return (clean_url, affiliate_url) from a scraped raw URL.

    clean_url keeps per-area identity params for ingest uniqueness.
    affiliate_url is the click-through destination (offer page, no identity params).
    """
    clean = strip_tracking_params(raw_url)
    affiliate = wrap_affiliate_url(clean, settings=settings)
    return clean, affiliate


def resolve_click_target(
    *,
    scraped_raw_url: str | None,
    affiliate_url: str | None,
    clean_url: str | None,
    settings: Settings | None = None,
) -> str | None:
    """Pick and sanitize the outbound URL for GET /go/{deal_id}."""
    # Prefer scraped_raw_url so hash fragments lost when affiliate_url was
    # built (older strip_tracking_params dropped fragments) can be recovered.
    source = scraped_raw_url or affiliate_url or clean_url
    if not source:
        return None
    wrapped = wrap_affiliate_url(source, settings=settings)
    return wrapped or None
