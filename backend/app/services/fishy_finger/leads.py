"""Select, dedupe, and store Fishy Finger Sub leads.

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

import asyncio
import concurrent.futures
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import replace
from typing import Any, Callable

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.models.deal import Deal
from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant
from app.scrapers.categories import CATEGORY_ORDER
from app.scrapers.zones import SCRAPE_ZONES, iter_zone_areas
from app.services.fishy_finger.chains import (
    ChainSignals,
    brand_key,
    chain_exclusion_reason,
    corporate_domain,
)
from app.services.fishy_finger.constants import FISHY_FINGER_SEGMENT
from app.services.fishy_finger.discover import (
    discover_fishy_candidates,
    emails_from_html,
    fetch_homepage,
)
from app.services.fishy_finger.email_quality import pick_best_email
from app.services.fishy_finger.types import AcceptedLead, VenueCandidate
from app.services.geo_names import normalize_city, normalize_country
from app.services.marketing_contacts import _clean_phone, _clean_website

logger = logging.getLogger(__name__)


def _run_coro(coro: Any) -> Any:
    """Run discovery from the sync Celery worker. Same approach as scrape_runner."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()

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
        source_segment=FISHY_FINGER_SEGMENT,
        lead_zone=lead.zone_id[:64],
        email_quality_score=lead.email_quality_score,
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


def run_fishy_finger_zone(zone_id: str) -> dict[str, Any]:
    """Discover and store leads for one scrape zone. Does not touch deal cycles."""
    zone = zone_id.strip().lower()
    if zone not in SCRAPE_ZONES:
        logger.warning("Unknown fishy finger zone %r; skipping", zone_id)
        return {"zone": zone, "ok": True, "status": "skipped", "skipped": "unknown_zone"}

    areas = iter_zone_areas(zone)
    candidates: list[VenueCandidate] = []
    cities_failed: list[str] = []
    for country, city in areas:
        try:
            batch = _run_coro(discover_fishy_candidates(country, city, zone))
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
            logger.exception("Fishy discovery failed for %s / %s", country, city)
            cities_failed.append(f"{country}:{city}")
            continue
        candidates.extend(batch)

    candidates = enrich_candidates(candidates)

    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    inserted = 0
    skipped_known = 0
    with session_factory() as session:
        extra_brands, extra_domains = load_stored_chain_signals(session)
        accepted, stats = select_fishy_leads(
            candidates,
            extra_brand_cities=extra_brands,
            extra_domain_names=extra_domains,
        )
        known = load_known_identity_keys(session)
        for lead in accepted:
            if lead_is_known(lead, known):
                skipped_known += 1
                continue
            try:
                with session.begin_nested():
                    insert_fishy_lead(session, lead)
                _remember(known, lead)
                inserted += 1
            except IntegrityError:
                skipped_known += 1
                continue
        session.commit()

    summary = {
        "zone": zone,
        "label": SCRAPE_ZONES[zone]["label"],
        "ok": True,
        "status": "completed",
        "cities": len(areas),
        "candidates": len(candidates),
        "leads_inserted": inserted,
        "skipped_known": skipped_known,
        "cities_failed": cities_failed,
        "filter_stats": stats,
    }
    logger.info(
        "Fishy Finger zone %s: candidates=%s inserted=%s known=%s",
        zone,
        len(candidates),
        inserted,
        skipped_known,
    )
    return summary
