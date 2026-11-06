"""Lead records passed between discovery, filtering, and storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VenueCandidate:
    """One discovered venue before chain and email filters."""

    business_name: str
    country_code: str
    city: str
    venue_category: str
    zone_id: str
    website: str | None = None
    emails: tuple[str, ...] = ()
    phone: str | None = None
    page_text: str | None = None
    osm_brand: str | None = None
    osm_brand_wikidata: str | None = None
    operator: str | None = None
    # Homepage or menu HTML already fetched while looking for an email.
    homepage_html: str | None = None
    homepage_url: str | None = None


@dataclass(frozen=True)
class AcceptedLead:
    """Independent venue with an email worth storing."""

    business_name: str
    country_code: str
    city: str
    venue_category: str
    zone_id: str
    email: str
    email_quality_score: int
    website: str | None = None
    phone: str | None = None
    has_site_specials: bool | None = None
    specials_checked_at: datetime | None = None
