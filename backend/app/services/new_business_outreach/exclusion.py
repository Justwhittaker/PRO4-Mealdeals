"""Drop venues already on DineADeal, already stored, or opted out.

A lead is new only when it misses every one of these:

- fuzzy business name plus the same country and city as a merchant
  (every deal on the site belongs to a merchant)
- the same website domain as a merchant or an existing marketing contact
  (shared website builders do not count)
- the same email as a marketing contact, a merchant, an unsubscribed
  outreach row, a suppressed outreach row, or an unsubscribed newsletter
  address
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant
from app.models.newsletter import NewsletterSubscriber
from app.services.geo_names import normalize_city, normalize_country
from app.services.marketing_contacts import _clean_email
from app.services.new_business_outreach.chains import corporate_domain
from app.services.new_business_outreach.types import AcceptedLead

_NAME_STOP = frozenset(
    {
        "the",
        "and",
        "restaurant",
        "restaurants",
        "cafe",
        "cafes",
        "bistro",
        "bar",
        "ltd",
        "limited",
        "inc",
        "co",
        "company",
    }
)
_NAME_RATIO = 0.88


def normalize_business_name(name: str | None) -> str:
    text = (name or "").lower().replace("&", " and ")
    text = text.replace("é", "e").replace("è", "e").replace("á", "a")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    parts = [part for part in text.split() if part not in _NAME_STOP]
    return " ".join(parts)


def names_match(left: str | None, right: str | None) -> bool:
    a = normalize_business_name(left)
    b = normalize_business_name(right)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 6 and len(b) >= 6 and (a in b or b in a):
        return True
    return SequenceMatcher(None, a, b).ratio() >= _NAME_RATIO


def _city_key(country: str | None, city: str | None) -> tuple[str, str]:
    return (
        normalize_country(country or ""),
        normalize_city(city).lower() if city else "",
    )


@dataclass
class ExclusionIndex:
    merchant_emails: set[str] = field(default_factory=set)
    merchant_domains: set[str] = field(default_factory=set)
    merchant_names: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    contact_emails: set[str] = field(default_factory=set)
    contact_domains: set[str] = field(default_factory=set)
    contact_names: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    unsubscribed_emails: set[str] = field(default_factory=set)
    suppressed_emails: set[str] = field(default_factory=set)

    def add_merchant(
        self,
        *,
        name: str | None,
        country: str | None,
        city: str | None,
        website: str | None = None,
        email: str | None = None,
    ) -> None:
        cleaned = _clean_email(email)
        if cleaned:
            self.merchant_emails.add(cleaned)
        domain = corporate_domain(website)
        if domain:
            self.merchant_domains.add(domain)
        normalized = normalize_business_name(name)
        key = _city_key(country, city)
        if normalized and key[0] and key[1]:
            self.merchant_names.setdefault(key, []).append(normalized)

    def add_contact(
        self,
        *,
        name: str | None,
        country: str | None,
        city: str | None,
        website: str | None = None,
        email: str | None = None,
        unsubscribed: bool = False,
        suppressed: bool = False,
    ) -> None:
        cleaned = _clean_email(email)
        if cleaned:
            self.contact_emails.add(cleaned)
            if unsubscribed:
                self.unsubscribed_emails.add(cleaned)
            if suppressed:
                self.suppressed_emails.add(cleaned)
        domain = corporate_domain(website)
        if domain:
            self.contact_domains.add(domain)
        normalized = normalize_business_name(name)
        key = _city_key(country, city)
        if normalized and key[0] and key[1]:
            self.contact_names.setdefault(key, []).append(normalized)

    def add_unsubscribed_email(self, email: str | None) -> None:
        cleaned = _clean_email(email)
        if cleaned:
            self.unsubscribed_emails.add(cleaned)


def exclusion_reason(lead: AcceptedLead, index: ExclusionIndex) -> str | None:
    """Why this lead is not new, or None when it can be stored."""
    email = _clean_email(lead.email)
    if email and email in index.unsubscribed_emails:
        return "unsubscribed"
    if email and email in index.suppressed_emails:
        return "suppressed"
    if email and email in index.merchant_emails:
        return "already_on_site_email"
    domain = corporate_domain(lead.website)
    if domain and domain in index.merchant_domains:
        return "already_on_site_domain"
    key = _city_key(lead.country_code, lead.city)
    for existing in index.merchant_names.get(key, ()):
        if names_match(lead.business_name, existing):
            return "already_on_site_name"
    if email and email in index.contact_emails:
        return "existing_contact"
    if domain and domain in index.contact_domains:
        return "existing_contact"
    for existing in index.contact_names.get(key, ()):
        if names_match(lead.business_name, existing):
            return "existing_contact"
    return None


def load_blocked_emails(session: Session) -> tuple[set[str], set[str]]:
    """Unsubscribed and suppressed addresses. Emails only, in small reads."""
    unsubscribed: set[str] = set()
    suppressed: set[str] = set()
    outreach = session.execute(
        select(
            MarketingContact.email,
            MarketingContact.outreach_unsubscribed_at,
            MarketingContact.outreach_excluded_at,
        ).where(
            (MarketingContact.outreach_unsubscribed_at.is_not(None))
            | (MarketingContact.outreach_excluded_at.is_not(None))
        )
    ).all()
    for email, unsub_at, excluded_at in outreach:
        cleaned = _clean_email(email)
        if not cleaned:
            continue
        if unsub_at is not None:
            unsubscribed.add(cleaned)
        if excluded_at is not None:
            suppressed.add(cleaned)
    newsletters = session.execute(
        select(NewsletterSubscriber.email).where(
            NewsletterSubscriber.is_subscribed.is_(False)
        )
    ).all()
    for (email,) in newsletters:
        cleaned = _clean_email(email)
        if cleaned:
            unsubscribed.add(cleaned)
    return unsubscribed, suppressed


def load_country_index(
    session: Session,
    country_code: str,
    *,
    unsubscribed: set[str],
    suppressed: set[str],
) -> ExclusionIndex:
    """Merchants, deals, and contacts for one country. Columns only."""
    index = ExclusionIndex(
        unsubscribed_emails=set(unsubscribed),
        suppressed_emails=set(suppressed),
    )
    country = normalize_country(country_code)
    contacts = session.execute(
        select(
            MarketingContact.business_name,
            MarketingContact.country_code,
            MarketingContact.city,
            MarketingContact.website,
            MarketingContact.email,
            MarketingContact.outreach_unsubscribed_at,
            MarketingContact.outreach_excluded_at,
        ).where(MarketingContact.country_code == country)
    ).all()
    for name, row_country, city, website, email, unsub_at, excluded_at in contacts:
        index.add_contact(
            name=name,
            country=row_country,
            city=city,
            website=website,
            email=email,
            unsubscribed=unsub_at is not None,
            suppressed=excluded_at is not None,
        )
    merchants = session.execute(
        select(
            Merchant.name,
            Merchant.website,
            Merchant.email,
            Location.country_code,
            Location.city,
        )
        .join(Location, Merchant.location_id == Location.id)
        .where(Location.country_code == country)
    ).all()
    for name, website, email, row_country, city in merchants:
        index.add_merchant(
            name=name,
            country=row_country,
            city=city,
            website=website,
            email=email,
        )
    return index
