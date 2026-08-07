"""Affiliate URL cleaning and wrapping for regional networks."""

from __future__ import annotations

from enum import Enum
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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


class AffiliateNetwork(str, Enum):
    AMAZON = "amazon"
    BOOKING = "booking"
    AWIN = "awin"
    CJ = "cj"
    IMPACT = "impact"
    RAKUTEN = "rakuten"
    UNKNOWN = "unknown"


def strip_tracking_params(url: str) -> str:
    """Return a clean URL with common tracking query parameters removed."""
    parsed = urlparse(url)
    filtered = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key.lower() not in _TRACKING_PARAMS
    ]
    clean_query = urlencode(filtered)
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            "",  # drop fragment
        )
    )


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
    clean = strip_tracking_params(url)
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
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, "")
    )


def build_affiliate_urls(raw_url: str, settings: Settings | None = None) -> tuple[str, str]:
    """Return (clean_url, affiliate_url) from a scraped raw URL."""
    clean = strip_tracking_params(raw_url)
    affiliate = wrap_affiliate_url(clean, settings=settings)
    return clean, affiliate
