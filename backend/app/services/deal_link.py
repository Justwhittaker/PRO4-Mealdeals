"""Outbound deal URL normalization, classification, and reachability checks."""

from __future__ import annotations

import logging
import re
from enum import Enum
from urllib.parse import parse_qsl, unquote, urlparse, urlunparse

import httpx

from app.services.affiliate import strip_tracking_params

logger = logging.getLogger(__name__)

# Query params added by global_retail for dedup — strip before user click-through.
_SCRAPER_DEDUP_PARAMS = frozenset(
    {"city", "locality", "country", "utm_source", "utm_medium", "utm_campaign"}
)

_LOCALE_SEGMENT = re.compile(r"^[a-z]{2}(-[a-z]{2})?$", re.IGNORECASE)
_LISTING_ROOTS = frozenset(
    {
        "deals",
        "deal",
        "offers",
        "offer",
        "promotions",
        "promotion",
        "specials",
        "special",
        "vouchers",
        "voucher",
        "coupons",
        "coupon",
        "happy-hour",
        "happyhour",
        "menu",
        "menus",
        "our-menu",
        "food",
    }
)

_USER_AGENT = "DineADealBot/1.0 (+https://dineadeal.com/bot; link-check)"


class LinkKind(str, Enum):
    SPECIFIC = "specific"
    LISTING = "listing"
    HOMEPAGE = "homepage"


def normalize_outbound_url(url: str | None) -> str | None:
    """Strip tracking + scraper dedup params for URLs users actually visit."""
    if not url or not str(url).strip():
        return None
    cleaned = strip_tracking_params(str(url).strip())
    parsed = urlparse(cleaned)
    if not parsed.scheme or not parsed.netloc:
        return None
    filtered = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=False)
        if key.lower() not in _SCRAPER_DEDUP_PARAMS
    ]
    query = "&".join(f"{k}={v}" for k, v in filtered) if filtered else ""
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, "")
    )


def classify_deal_url(url: str | None) -> LinkKind:
    """Classify how specific the outbound URL is (for honest CTAs)."""
    if not url:
        return LinkKind.HOMEPAGE

    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return LinkKind.HOMEPAGE

    host = parsed.netloc.lower()
    if any(
        token in host
        for token in ("facebook.com", "instagram.com", "twitter.com", "x.com")
    ):
        return LinkKind.HOMEPAGE

    path = unquote(parsed.path or "/").lower().rstrip("/") or "/"
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return LinkKind.HOMEPAGE

    start = 0
    if _LOCALE_SEGMENT.fullmatch(segments[0]):
        start = 1
    if start >= len(segments):
        return LinkKind.HOMEPAGE

    root = segments[start]
    if root in _LISTING_ROOTS:
        if len(segments) > start + 1:
            return LinkKind.SPECIFIC
        return LinkKind.LISTING

    if len(segments) - start >= 2:
        return LinkKind.SPECIFIC

    return LinkKind.HOMEPAGE


def cta_label_for_link(link_kind: LinkKind | str, merchant_name: str) -> str:
    kind = LinkKind(link_kind) if isinstance(link_kind, str) else link_kind
    name = (merchant_name or "this venue").strip() or "this venue"
    if kind is LinkKind.SPECIFIC:
        return "Claim this deal"
    if kind is LinkKind.LISTING:
        return f"View offers on {name}"
    return f"Visit {name} website"


def check_url_reachable(url: str, *, timeout: float = 10.0) -> bool:
    """Return True when the URL responds (HEAD, then GET fallback)."""
    if not url or not url.strip():
        return False

    headers = {"User-Agent": _USER_AGENT}
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        ) as client:
            try:
                response = client.head(url)
                if response.status_code < 400:
                    return True
                if response.status_code in {405, 403, 501}:
                    response = client.get(url)
            except httpx.HTTPError:
                response = client.get(url)

            return response.status_code < 400
    except httpx.HTTPError as exc:
        logger.info("URL unreachable %s: %s", url, exc)
        return False


def outbound_link_meta(
    *,
    affiliate_url: str | None,
    clean_url: str | None,
    scraped_raw_url: str | None,
) -> tuple[str | None, LinkKind]:
    source = affiliate_url or clean_url or scraped_raw_url
    outbound = normalize_outbound_url(source)
    if not outbound:
        return None, LinkKind.HOMEPAGE
    return outbound, classify_deal_url(outbound)
