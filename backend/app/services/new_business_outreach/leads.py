"""Select, dedupe, and store New Business Outreach leads.

Rows stay lean: name, type, address, website, email, source, and the
existing marketing-contact columns. Homepage HTML is used in memory to find
an email and is not written to Postgres.

A lead is stored only when all of the following hold:

- The venue category is one of the hospitality parents in ``CATEGORY_ORDER``.
- Chain and group heuristics in ``chains.py`` do not match.
- At least one email passes ``email_quality.pick_best_email``.
- The business is not already on the site: no non-deleted deal matches the
  name, website, or email in that city, and no ``marketing_contacts`` row
  matches email, website+city, or name+city.

Homepage fetches fill a missing email. They are capped per city so a zone
does not crawl every OSM website. Social and builder hosts are not treated
as a shared corporate domain; see ``chains.py``.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import replace
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant
from app.scrapers.categories import CATEGORY_ORDER
from app.services.new_business_outreach.chains import (
    ChainSignals,
    brand_key,
    chain_exclusion_reason,
    corporate_domain,
)
from app.services.new_business_outreach.constants import NEW_BUSINESS_SEGMENT
from app.services.new_business_outreach.discover import (
    contact_page_urls,
    emails_from_html,
    fetch_homepage,
)
from app.services.new_business_outreach.email_quality import pick_best_email
from app.services.new_business_outreach.types import AcceptedLead, VenueCandidate
from app.services.geo_names import normalize_city, normalize_country
from app.services.marketing_contacts import _clean_phone, _clean_website

# Venues with no OSM email: at most this many homepage reads per city.
HOMEPAGE_FETCHES_PER_CITY = 8

HomepageFetch = Callable[[str], tuple[str, str] | None]


def _city_key(country_code: str, city: str) -> tuple[str, str]:
    return (normalize_country(country_code), normalize_city(city).lower())


def _page_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()[:4000]


def enrich_candidates(
    candidates: list[VenueCandidate],
    *,
    fetch: HomepageFetch | None = None,
    per_city_limit: int = HOMEPAGE_FETCHES_PER_CITY,
) -> list[VenueCandidate]:
    """Fetch homepages only for venues that do not already have a usable email."""
    getter = fetch or fetch_homepage
    used: dict[tuple[str, str], int] = defaultdict(int)
    enriched: list[VenueCandidate] = []
    for candidate in candidates:
        if pick_best_email(candidate.emails).accepted:
            enriched.append(candidate)
            continue
        if not candidate.website:
            enriched.append(candidate)
            continue
        key = _city_key(candidate.country_code, candidate.city)
        if used[key] >= per_city_limit:
            enriched.append(candidate)
            continue
        used[key] += 1
        fetched = getter(candidate.website)
        if not fetched:
            enriched.append(candidate)
            continue
        final_url, html = fetched
        emails = tuple(dict.fromkeys((*candidate.emails, *emails_from_html(html))))
        enriched.append(
            replace(
                candidate,
                website=final_url or candidate.website,
                emails=emails,
                page_text=_page_text(html),
                homepage_html=html,
                homepage_url=final_url or candidate.website,
            )
        )
    return enriched


def enrich_contact_pages(
    candidates: list[VenueCandidate],
    *,
    fetch: HomepageFetch | None = None,
    per_city_limit: int = 4,
) -> list[VenueCandidate]:
    """One contact page and one about page when the homepage had no usable email."""
    getter = fetch or fetch_homepage
    used: dict[tuple[str, str], int] = defaultdict(int)
    enriched: list[VenueCandidate] = []
    for candidate in candidates:
        if pick_best_email(candidate.emails).accepted or not candidate.website:
            enriched.append(candidate)
            continue
        key = _city_key(candidate.country_code, candidate.city)
        emails = list(candidate.emails)
        extra_text = ""
        found = False
        for url in contact_page_urls(candidate.website)[:2]:
            if used[key] >= per_city_limit:
                break
            used[key] += 1
            fetched = getter(url)
            if not fetched:
                continue
            _final, html = fetched
            extra_text = f"{extra_text} {_page_text(html)}".strip()
            emails.extend(emails_from_html(html))
            if pick_best_email(emails).accepted:
                found = True
                break
        if not found and not extra_text:
            enriched.append(candidate)
            continue
        enriched.append(
            replace(
                candidate,
                emails=tuple(dict.fromkeys(emails)),
                page_text=_page_text(f"{candidate.page_text or ''} {extra_text}"),
                lead_source="website" if pick_best_email(emails).accepted else candidate.lead_source,
            )
        )
    return enriched


def _batch_signal_sets(
    candidates: list[VenueCandidate],
) -> tuple[dict[str, set[tuple[str, str]]], dict[str, set[str]]]:
    brand_cities: dict[str, set[tuple[str, str]]] = defaultdict(set)
    domain_names: dict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        key = brand_key(candidate.osm_brand or candidate.business_name)
        if key:
            brand_cities[key].add(_city_key(candidate.country_code, candidate.city))
        domain = corporate_domain(candidate.website)
        if domain and key:
            domain_names[domain].add(key)
    return brand_cities, domain_names


def select_fishy_leads(
    candidates: list[VenueCandidate],
    *,
    extra_brand_cities: dict[str, set[tuple[str, str]]] | None = None,
    extra_domain_names: dict[str, set[str]] | None = None,
) -> tuple[list[AcceptedLead], dict[str, int]]:
    """Drop chains, groups, out-of-category venues, and bad emails.

    ``extra_brand_cities`` and ``extra_domain_names`` are businesses already
    stored, so a brand spread across earlier weeks still counts. The returned
    counter maps each exclusion reason to how many venues in this batch hit it.
    ``kept`` is the number stored as :class:`AcceptedLead`.
    """
    brand_cities, domain_names = _batch_signal_sets(candidates)
    for key, cities in (extra_brand_cities or {}).items():
        if key:
            brand_cities[key].update(cities)
    for domain, names in (extra_domain_names or {}).items():
        if domain:
            domain_names[domain].update(names)
    brand_counts = {key: len(cities) for key, cities in brand_cities.items()}
    domain_counts = {domain: len(names) for domain, names in domain_names.items()}
    accepted: list[AcceptedLead] = []
    stats: dict[str, int] = defaultdict(int)
    seen_emails: set[str] = set()
    for candidate in candidates:
        category = (candidate.venue_category or "").strip()
        if category not in CATEGORY_ORDER:
            stats["category"] += 1
            continue
        key = brand_key(candidate.osm_brand or candidate.business_name)
        domain = corporate_domain(candidate.website)
        reason = chain_exclusion_reason(
            business_name=candidate.business_name,
            website=candidate.website,
            page_text=candidate.page_text,
            osm_brand=candidate.osm_brand,
            osm_brand_wikidata=candidate.osm_brand_wikidata,
            operator=candidate.operator,
            signals=ChainSignals(
                brand_city_count=brand_counts.get(key, 1) if key else 1,
                domain_venue_count=domain_counts.get(domain, 1) if domain else 1,
            ),
        )
        if reason:
            stats[reason] += 1
            continue
        verdict = pick_best_email(candidate.emails)
        if not verdict.accepted or not verdict.email:
            stats["email"] += 1
            continue
        if verdict.email in seen_emails:
            stats["duplicate_email"] += 1
            continue
        seen_emails.add(verdict.email)
        accepted.append(
            AcceptedLead(
                business_name=candidate.business_name.strip(),
                country_code=normalize_country(candidate.country_code),
                city=normalize_city(candidate.city),
                venue_category=category,
                zone_id=candidate.zone_id.strip().lower(),
                email=verdict.email,
                email_quality_score=verdict.score,
                website=_clean_website(candidate.website),
                phone=_clean_phone(candidate.phone),
                address=candidate.address,
                tile_id=candidate.tile_id,
                lead_source=candidate.lead_source,
            )
        )
    stats["kept"] = len(accepted)
    return accepted, dict(stats)


def identity_keys(
    *,
    email: str | None,
    website: str | None,
    name: str | None,
    country_code: str | None,
    city: str | None,
) -> set[tuple[str, str]]:
    """Keys that mean this business is already a contact or already has a deal."""
    keys: set[tuple[str, str]] = set()
    country = normalize_country(country_code or "")
    city_name = normalize_city(city).lower() if city else ""
    cleaned_email = (email or "").strip().lower()
    if cleaned_email:
        keys.add(("email", cleaned_email))
    site = _clean_website(website)
    if site and country and city_name:
        keys.add(("website", f"{site}|{country}|{city_name}"))
    business = (name or "").strip().lower()
    if business and country and city_name:
        keys.add(("name", f"{business}|{country}|{city_name}"))
    return keys


def lead_is_known(lead: AcceptedLead, known: set[tuple[str, str]]) -> bool:
    return bool(
        identity_keys(
            email=lead.email,
            website=lead.website,
            name=lead.business_name,
            country_code=lead.country_code,
            city=lead.city,
        )
        & known
    )


def load_stored_chain_signals(
    session: Session,
) -> tuple[dict[str, set[tuple[str, str]]], dict[str, set[str]]]:
    """Brand cities and corporate domains already on file.

    Marketing contacts count even without a deal. Merchants count only when
    they already have a non-deleted deal, which is "on the site".
    """
    brand_cities: dict[str, set[tuple[str, str]]] = defaultdict(set)
    domain_names: dict[str, set[str]] = defaultdict(set)

    def _add(name: str | None, website: str | None, country: str | None, city: str | None) -> None:
        key = brand_key(name)
        if key and country and city:
            brand_cities[key].add(_city_key(country, city))
        domain = corporate_domain(website)
        if domain and key:
            domain_names[domain].add(key)

    contacts = session.execute(
        select(
            MarketingContact.business_name,
            MarketingContact.website,
            MarketingContact.country_code,
            MarketingContact.city,
        )
    ).all()
    for name, website, country, city in contacts:
        _add(name, website, country, city)
    deals = session.execute(
        select(
            Merchant.name,
            Merchant.website,
            Location.country_code,
            Location.city,
        )
        .join(Location, Merchant.location_id == Location.id)
        .join(Deal, Deal.merchant_id == Merchant.id)
        .where(Deal.deleted_at.is_(None))
    ).all()
    for name, website, country, city in deals:
        _add(name, website, country, city)
    return brand_cities, domain_names


def load_known_identity_keys(session: Session) -> set[tuple[str, str]]:
    """Marketing contacts, plus any merchant that already has a live deal."""
    keys: set[tuple[str, str]] = set()
    contacts = session.execute(
        select(
            MarketingContact.email,
            MarketingContact.website,
            MarketingContact.business_name,
            MarketingContact.country_code,
            MarketingContact.city,
        )
    ).all()
    for email, website, name, country, city in contacts:
        keys |= identity_keys(
            email=email,
            website=website,
            name=name,
            country_code=country,
            city=city,
        )
    deals = session.execute(
        select(
            Merchant.email,
            Merchant.website,
            Merchant.name,
            Location.country_code,
            Location.city,
        )
        .join(Location, Merchant.location_id == Location.id)
        .join(Deal, Deal.merchant_id == Merchant.id)
        .where(Deal.deleted_at.is_(None))
    ).all()
    for email, website, name, country, city in deals:
        keys |= identity_keys(
            email=email,
            website=website,
            name=name,
            country_code=country,
            city=city,
        )
    return keys


def insert_fishy_lead(session: Session, lead: AcceptedLead) -> MarketingContact:
    """Insert one new lead. Caller skips rows that are already known."""
    row = MarketingContact(
        id=uuid.uuid4(),
        business_name=lead.business_name[:255],
        website=lead.website,
        phone=lead.phone,
        email=lead.email,
        country_code=lead.country_code,
        city=lead.city,
        source_url=lead.website,
        venue_category=lead.venue_category[:120],
        source_segment=NEW_BUSINESS_SEGMENT,
        lead_zone=lead.zone_id[:64],
        email_quality_score=lead.email_quality_score,
        has_site_specials=lead.has_site_specials,
        specials_checked_at=lead.specials_checked_at,
        lead_address=(lead.address[:255] if lead.address else None),
        lead_tile=(lead.tile_id[:64] if lead.tile_id else None),
        lead_source=(lead.lead_source[:32] if lead.lead_source else None),
    )
    session.add(row)
    session.flush()
    return row


def _remember(known: set[tuple[str, str]], lead: AcceptedLead) -> None:
    known |= identity_keys(
        email=lead.email,
        website=lead.website,
        name=lead.business_name,
        country_code=lead.country_code,
        city=lead.city,
    )
