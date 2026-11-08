"""Whether a venue is already promoting specials on its own site.

The only HTTP this adds is the deal scraper's existing listing probes:
``/offers``, ``/specials``, and ``/deals``. Offer links and offer copy on a
homepage or menu page are read from HTML this run already fetched. No other
path is requested.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.task_errors import reraise_if_fatal
from app.scrapers.global_retail import _OFFER_SNIPPET_RE
from app.scrapers.offer_links import extract_offer_url_from_soup, listing_urls_for
from app.scrapers.politeness import pace_host_sync
from app.services.new_business_outreach.discover import (
    _HOMEPAGE_BYTES,
    _USER_AGENT,
    _public_http_url,
)
from app.services.new_business_outreach.types import AcceptedLead, VenueCandidate

logger = logging.getLogger(__name__)

ProbeKind = Literal["offer", "empty", "not_found", "error"]

# Same three paths the scraper already guesses. listing_urls_for also emits
# /promotions, /vouchers, /menu, and the homepage; those are not requested here.
SPECIALS_PROBE_PATHS: tuple[str, ...] = ("/offers", "/specials", "/deals")

_NOT_FOUND_STATUSES = frozenset({403, 404, 410, 451})

HttpGet = Callable[[str], tuple[int | None, str | None, str | None]]


@dataclass(frozen=True)
class ProbeResult:
    """One listing-path response, already classified."""

    path: str
    kind: ProbeKind


def specials_probe_urls(website: str) -> list[str]:
    """``/offers``, ``/specials``, and ``/deals`` on the venue origin, in that order."""
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    for url in listing_urls_for(website):
        path = urlparse(url).path.rstrip("/").lower()
        for index, suffix in enumerate(SPECIALS_PROBE_PATHS):
            # Exact path or a language prefix (/en/offers). Deeper paths such
            # as /offers/lunch are not produced by listing_urls_for.
            if path != suffix and not path.endswith(suffix):
                continue
            if url not in seen:
                seen.add(url)
                found.append((index, url))
            break
    found.sort(key=lambda item: item[0])
    return [url for _index, url in found]


def offer_found_in_html(html: str | None, page_url: str) -> bool:
    """True when the scraper's offer extractor or offer-snippet copy matches."""
    if not html or not html.strip():
        return False
    soup = BeautifulSoup(html, "html.parser")
    try:
        extracted = extract_offer_url_from_soup(soup, page_url=page_url)
    except Exception as exc:  # noqa: BLE001 — one bad href must not drop the lead
        reraise_if_fatal(exc)
        logger.debug("Offer extract failed for %s", page_url, exc_info=True)
        extracted = None
    if extracted:
        return True
    text = soup.get_text(" ", strip=True)
    return _OFFER_SNIPPET_RE.search(text) is not None


def probe_kind(
    *,
    status_code: int | None,
    html: str | None,
    page_url: str,
    error: str | None = None,
) -> ProbeKind:
    """Map one response to offer, empty, not_found, or error.

    Timeout, transport failure, and 5xx are errors (the flag stays unknown).
    404 and the scraper's other miss statuses are not_found. A 2xx page is an
    offer only when offer content was extracted.
    """
    if error or status_code is None:
        return "error"
    if status_code >= 500 or status_code in {408, 429}:
        return "error"
    if status_code in _NOT_FOUND_STATUSES:
        return "not_found"
    if status_code >= 400:
        return "error"
    if offer_found_in_html(html, page_url):
        return "offer"
    return "empty"


def classify_site_specials(
    probes: Sequence[ProbeResult],
    *,
    crawled_pages: Sequence[tuple[str, str]] = (),
) -> bool | None:
    """True if any offer was found, false if every check was empty, else unknown.

    Crawled pages are homepage or menu HTML already fetched. An offer there
    wins even when the three probes 404. Any timeout or 5xx with no offer
    returns None. No probes and no crawled HTML also returns None.
    """
    for page_url, html in crawled_pages:
        if offer_found_in_html(html, page_url):
            return True
    if any(probe.kind == "offer" for probe in probes):
        return True
    if any(probe.kind == "error" for probe in probes):
        return None
    if not probes and not crawled_pages:
        return None
    conclusive = {"not_found", "empty"}
    if probes and all(probe.kind in conclusive for probe in probes):
        return False
    if crawled_pages and not probes:
        return False
    return None


def _http_get(url: str) -> tuple[int | None, str | None, str | None]:
    """GET one probe URL. ``error`` is set on timeout or transport failure."""
    if not _public_http_url(url):
        return None, None, "unsafe_url"
    pace_host_sync(url)
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": _USER_AGENT})
    except httpx.TimeoutException:
        return None, None, "timeout"
    except Exception as exc:  # noqa: BLE001 — one dead host must not abort the zone
        reraise_if_fatal(exc)
        logger.info("Fishy specials probe failed for %s: %s", url, exc)
        return None, None, "transport"
    return response.status_code, response.text[:_HOMEPAGE_BYTES], None


def fetch_specials_probes(website: str, *, get: HttpGet | None = None) -> list[ProbeResult]:
    """Probe only ``/offers``, ``/specials``, and ``/deals``."""
    getter = get or _http_get
    results: list[ProbeResult] = []
    for url in specials_probe_urls(website):
        try:
            status, html, error = getter(url)
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
            logger.info("Fishy specials probe failed for %s: %s", url, exc)
            status, html, error = None, None, "transport"
        results.append(
            ProbeResult(
                path=urlparse(url).path or url,
                kind=probe_kind(
                    status_code=status,
                    html=html,
                    page_url=url,
                    error=error,
                ),
            )
        )
    return results


def _crawled_pages(candidate: VenueCandidate | None) -> tuple[tuple[str, str], ...]:
    """Homepage or menu HTML already fetched for this venue. No new request."""
    if candidate is None or not candidate.homepage_html:
        return ()
    page_url = candidate.homepage_url or candidate.website or ""
    if not page_url:
        return ()
    return ((page_url, candidate.homepage_html),)


def annotate_leads_with_specials(
    leads: list[AcceptedLead],
    candidates: list[VenueCandidate],
    *,
    probe: Callable[[str], list[ProbeResult]] | None = None,
    now: datetime | None = None,
) -> list[AcceptedLead]:
    """Set ``has_site_specials`` from probes plus HTML already crawled."""
    prober = probe or fetch_specials_probes
    checked_at = now or datetime.now(timezone.utc)
    by_email: dict[str, VenueCandidate] = {}
    by_site: dict[str, VenueCandidate] = {}
    for candidate in candidates:
        for email in candidate.emails:
            by_email.setdefault(email.lower(), candidate)
        if candidate.website:
            by_site.setdefault(candidate.website.lower(), candidate)

    annotated: list[AcceptedLead] = []
    for lead in leads:
        candidate = by_email.get(lead.email.lower())
        if candidate is None and lead.website:
            candidate = by_site.get(lead.website.lower())
        pages = _crawled_pages(candidate)
        if not lead.website and not pages:
            annotated.append(lead)
            continue
        probes: list[ProbeResult] = []
        if lead.website:
            try:
                probes = list(prober(lead.website))
            except Exception as exc:  # noqa: BLE001
                reraise_if_fatal(exc)
                logger.info("Fishy specials probe failed for %s: %s", lead.website, exc)
                probes = [ProbeResult(path=lead.website, kind="error")]
        flag = classify_site_specials(probes, crawled_pages=pages)
        annotated.append(
            replace(
                lead,
                has_site_specials=flag,
                specials_checked_at=checked_at,
            )
        )
    return annotated
