"""Resolve merchant listing/home pages to concrete offer URLs where possible."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urljoin, urlparse

from app.services.deal_link import LinkKind, classify_deal_url, normalize_outbound_url

logger = logging.getLogger(__name__)

_LISTING_PATHS = (
    "/deals",
    "/offers",
    "/promotions",
    "/specials",
    "/vouchers",
    "/coupons",
    "/happy-hour",
    "/happyhour",
    "/menu",
)

_OFFER_TEXT_RE = re.compile(
    r"(?i)\b("
    r"deal|deals|offer|offers|promo|promotion|special|specials|"
    r"voucher|coupon|happy\s*hour|2[\s-]*for[\s-]*1|bogo|buy\s*one|"
    r"half\s*price|\d+\s*%\s*off|meal\s*deal|lunch\s*deal|bundle"
    r")\b"
)

_SKIP_HREF_RE = re.compile(
    r"(?i)(login|sign[\s-]?in|register|signup|cart|checkout|privacy|terms|"
    r"cookie|careers|contact|facebook|instagram|twitter|linkedin|youtube|"
    r"\.pdf$|mailto:|tel:)"
)


def _same_site(origin: str, candidate: str) -> bool:
    try:
        return urlparse(origin).netloc.lower() == urlparse(candidate).netloc.lower()
    except Exception:  # noqa: BLE001
        return False


def _origin_of(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    return f"{parsed.scheme}://{parsed.netloc}"


def listing_urls_for(base_url: str) -> list[str]:
    """Candidate promo listing pages on the same host."""
    origin = _origin_of(base_url)
    parsed = urlparse(base_url)
    prefix = ""
    segments = [s for s in (parsed.path or "").split("/") if s]
    if segments and re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", segments[0], re.I):
        prefix = f"/{segments[0]}"
    seen: set[str] = set()
    out: list[str] = []
    for suffix in _LISTING_PATHS:
        candidate = normalize_outbound_url(f"{origin}{prefix}{suffix}") or ""
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
    normalized_base = normalize_outbound_url(base_url) or base_url
    if normalized_base not in seen:
        out.insert(0, normalized_base)
    return out


def _score_offer_candidate(href: str, anchor_text: str, *, page_url: str) -> int:
    if not href or _SKIP_HREF_RE.search(href):
        return -1
    absolute = normalize_outbound_url(urljoin(page_url, href))
    if not absolute or not _same_site(page_url, absolute):
        return -1
    text = f"{absolute} {anchor_text}".strip()
    if not _OFFER_TEXT_RE.search(text):
        return -1
    score = 10
    path = urlparse(absolute).path.lower()
    if any(token in path for token in ("deal", "offer", "promo", "special", "voucher")):
        score += 8
    depth = len([s for s in path.split("/") if s])
    if depth >= 3:
        score += 6
    elif depth == 2:
        score += 3
    if classify_deal_url(absolute) is LinkKind.SPECIFIC:
        score += 12
    elif classify_deal_url(absolute) is LinkKind.LISTING:
        score += 4
    if anchor_text and _OFFER_TEXT_RE.search(anchor_text):
        score += 4
    return score


def extract_offer_url_from_soup(soup: Any, *, page_url: str) -> str | None:
    """Best same-site offer link on a page, if any."""
    best_url: str | None = None
    best_score = 0
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        text = anchor.get_text(" ", strip=True)[:200]
        score = _score_offer_candidate(href, text, page_url=page_url)
        if score <= best_score:
            continue
        absolute = normalize_outbound_url(urljoin(page_url, href))
        if not absolute:
            continue
        best_score = score
        best_url = absolute
    return best_url


async def resolve_offer_url(
    base_url: str,
    fetch_html: Callable[[str], Awaitable[str]],
    *,
    parse_soup: Callable[[str], Any],
    max_extra_fetches: int = 4,
) -> str | None:
    """
    Try base URL then common listing paths; return the best offer URL found.

    Returns None when only homepage/listing pages were seen (no deep link).
    """
    normalized = normalize_outbound_url(base_url) or base_url
    candidates = listing_urls_for(normalized)[: max(1, max_extra_fetches + 1)]
    best_url: str | None = None
    best_score = 0

    for page_url in candidates:
        try:
            html = await fetch_html(page_url)
        except Exception as exc:  # noqa: BLE001
            logger.info("Deep scrape fetch skipped %s: %s", page_url, exc)
            continue
        if not html or len(html) < 200:
            continue
        soup = parse_soup(html)
        offer = extract_offer_url_from_soup(soup, page_url=page_url)
        if offer:
            score = _score_offer_candidate(offer, "", page_url=page_url) + 20
            if score > best_score:
                best_score = score
                best_url = offer
            if classify_deal_url(offer) is LinkKind.SPECIFIC:
                return offer
        kind = classify_deal_url(page_url)
        if kind is LinkKind.LISTING and not offer:
            listing_score = 15
            if listing_score > best_score:
                best_score = listing_score
                best_url = page_url

    if best_url and classify_deal_url(best_url) is not LinkKind.HOMEPAGE:
        return best_url
    return None
