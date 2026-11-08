"""Website lookups that did not fit in this week's fetch budget."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.website_queue import NewBusinessWebsiteQueue
from app.services.new_business_outreach.discover import (
    contact_page_urls,
    emails_from_html,
    fetch_homepage,
)
from app.services.new_business_outreach.email_quality import pick_best_email
from app.services.new_business_outreach.tiles import FETCHES_PER_PLACE
from app.services.new_business_outreach.types import VenueCandidate

QUEUE_BATCH = 20


@dataclass
class FetchBudget:
    remaining: int

    def __post_init__(self) -> None:
        self.remaining = max(int(self.remaining), 0)


def attempt_website(
    candidate: VenueCandidate,
    budget: FetchBudget,
    *,
    fetch=fetch_homepage,
) -> tuple[VenueCandidate, str]:
    """Look up an email. Returns ``skipped``, ``partial``, or ``done``.

    ``skipped`` means the budget was already empty, so the place stays queued.
    ``partial`` means the budget ran out before the contact pages, so it is
    queued again. ``done`` means every allowed page was tried or an email
    was found.
    """
    if budget.remaining <= 0:
        return candidate, "skipped"
    pages = [candidate.website or ""]
    pages.extend(contact_page_urls(candidate.website or "")[: FETCHES_PER_PLACE - 1])
    emails = list(candidate.emails)
    html = candidate.homepage_html
    final = candidate.website
    started = False
    for url in pages:
        if not url:
            continue
        if pick_best_email(emails).accepted:
            break
        if budget.remaining <= 0:
            return _with_pages(candidate, emails, html, final), "partial"
        budget.remaining -= 1
        started = True
        fetched = fetch(url)
        if not fetched:
            continue
        final, html = fetched
        emails.extend(emails_from_html(html))
    if not started:
        return candidate, "skipped"
    return _with_pages(candidate, emails, html, final), "done"


def _with_pages(
    candidate: VenueCandidate,
    emails: list[str],
    html: str | None,
    final: str | None,
) -> VenueCandidate:
    accepted = pick_best_email(emails).accepted
    source = "website" if accepted else candidate.lead_source
    return replace(
        candidate,
        emails=tuple(dict.fromkeys(emails)),
        website=final or candidate.website,
        homepage_html=html,
        homepage_url=final or candidate.website,
        lead_source=source,
    )


def row_to_candidate(row: NewBusinessWebsiteQueue) -> VenueCandidate:
    email = (row.osm_email or "").strip()
    return VenueCandidate(
        business_name=row.business_name,
        country_code=row.country_code,
        city=row.city or "",
        venue_category=row.venue_category or "",
        zone_id=row.lead_zone or "",
        website=row.website,
        emails=(email,) if email else (),
        phone=row.phone,
        osm_brand=row.osm_brand,
        osm_brand_wikidata=row.osm_brand_wikidata,
        operator=row.osm_operator,
        address=row.lead_address,
        tile_id=row.lead_tile,
        lead_source="osm" if email else None,
    )


def candidate_to_row(candidate: VenueCandidate) -> NewBusinessWebsiteQueue:
    email = candidate.emails[0] if candidate.emails else None
    return NewBusinessWebsiteQueue(
        id=uuid.uuid4(),
        business_name=candidate.business_name[:255],
        country_code=candidate.country_code[:8],
        city=(candidate.city or "")[:120] or None,
        venue_category=(candidate.venue_category or "")[:120] or None,
        lead_zone=(candidate.zone_id or "")[:64] or None,
        lead_tile=(candidate.tile_id or "")[:64] or None,
        website=(candidate.website or "")[:500] or None,
        osm_email=(email or "")[:255] or None,
        phone=(candidate.phone or "")[:64] or None,
        lead_address=(candidate.address or "")[:255] or None,
        osm_brand=(candidate.osm_brand or "")[:120] or None,
        osm_brand_wikidata=(candidate.osm_brand_wikidata or "")[:64] or None,
        osm_operator=(candidate.operator or "")[:255] or None,
    )


def enqueue_candidates(session: Session, candidates: list[VenueCandidate]) -> int:
    """Batch-insert places that still need a website. Returns how many queued."""
    queued = 0
    batch: list[NewBusinessWebsiteQueue] = []
    for candidate in candidates:
        if not candidate.website:
            continue
        batch.append(candidate_to_row(candidate))
        if len(batch) >= QUEUE_BATCH:
            session.add_all(batch)
            session.commit()
            queued += len(batch)
            batch = []
    if batch:
        session.add_all(batch)
        session.commit()
        queued += len(batch)
    return queued


def next_queue_rows(session: Session, limit: int) -> list[NewBusinessWebsiteQueue]:
    if limit <= 0:
        return []
    return list(
        session.scalars(
            select(NewBusinessWebsiteQueue)
            .order_by(NewBusinessWebsiteQueue.created_at, NewBusinessWebsiteQueue.id)
            .limit(limit)
        ).all()
    )
