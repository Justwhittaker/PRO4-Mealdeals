"""Upsert and export scraped hospitality business contacts."""

from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.marketing_contact import MarketingContact
from app.scrapers.base import ScrapedDeal
from app.services.ingest import normalize_city, normalize_country

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_email(value: str | None) -> str | None:
    if not value:
        return None
    email = value.strip().lower()
    if email.startswith("mailto:"):
        email = email[7:]
    email = email.split("?")[0].strip()
    return email if _EMAIL_RE.match(email) else None


def _clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    phone = value.strip()
    if phone.lower().startswith("tel:"):
        phone = phone[4:]
    phone = re.sub(r"[^\d+()\-\s]", "", phone).strip()
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7:
        return None
    return phone[:64]


def _clean_website(value: str | None) -> str | None:
    if not value:
        return None
    url = value.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url[:500]


def upsert_marketing_contact(
    session: Session,
    *,
    business_name: str,
    website: str | None,
    phone: str | None,
    email: str | None,
    about_blurb: str | None,
    country_code: str,
    city: str | None,
    source_url: str | None = None,
    venue_category: str | None = None,
) -> MarketingContact | None:
    """Insert or refresh one marketing contact. Returns None if name missing."""
    name = (business_name or "").strip()
    if not name:
        return None

    country = normalize_country(country_code)
    city_name = normalize_city(city) if city else None
    website_clean = _clean_website(website)
    email_clean = _clean_email(email)
    phone_clean = _clean_phone(phone)
    blurb = (about_blurb or "").strip()[:600] or None

    existing: MarketingContact | None = None
    if email_clean:
        existing = session.execute(
            select(MarketingContact)
            .where(MarketingContact.email == email_clean)
            .limit(1)
        ).scalar_one_or_none()
    if existing is None and website_clean:
        existing = session.execute(
            select(MarketingContact)
            .where(
                MarketingContact.website == website_clean,
                MarketingContact.country_code == country,
                MarketingContact.city == city_name,
            )
            .limit(1)
        ).scalar_one_or_none()
    if existing is None:
        existing = session.execute(
            select(MarketingContact)
            .where(
                MarketingContact.business_name == name[:255],
                MarketingContact.country_code == country,
                MarketingContact.city == city_name,
            )
            .limit(1)
        ).scalar_one_or_none()

    now = _utcnow()
    if existing:
        existing.business_name = name[:255]
        if website_clean:
            existing.website = website_clean
        if phone_clean:
            existing.phone = phone_clean
        if email_clean:
            existing.email = email_clean
        if blurb:
            existing.about_blurb = blurb
        if source_url:
            existing.source_url = source_url[:500]
        if venue_category:
            existing.venue_category = venue_category[:120]
        existing.last_scraped_at = now
        session.flush()
        return existing

    row = MarketingContact(
        id=uuid.uuid4(),
        business_name=name[:255],
        website=website_clean,
        phone=phone_clean,
        email=email_clean,
        about_blurb=blurb,
        country_code=country,
        city=city_name,
        source_url=(source_url[:500] if source_url else None),
        venue_category=(venue_category[:120] if venue_category else None),
        last_scraped_at=now,
    )
    session.add(row)
    session.flush()
    return row


def ingest_marketing_contacts_from_deals(
    session: Session, deals: Sequence[ScrapedDeal]
) -> int:
    """Persist marketing contacts from scraped deal payloads."""
    count = 0
    for deal in deals:
        try:
            row = upsert_marketing_contact(
                session,
                business_name=deal.merchant_name,
                website=deal.website or deal.raw_url,
                phone=deal.phone,
                email=deal.email,
                about_blurb=deal.about_blurb,
                country_code=deal.country_code,
                city=deal.city,
                source_url=deal.raw_url,
                venue_category=deal.venue_category,
            )
            if row is not None:
                count += 1
        except Exception:
            logger.exception(
                "Failed to upsert marketing contact for %s", deal.merchant_name
            )
    session.commit()
    logger.info("Upserted %d marketing contacts", count)
    return count


def export_marketing_contacts_csv(
    session: Session,
    *,
    country_code: str | None = None,
) -> str:
    """Return CSV of name / phone / email (+ helpful context columns)."""
    stmt = select(MarketingContact).order_by(
        MarketingContact.country_code.asc(),
        MarketingContact.business_name.asc(),
    )
    if country_code:
        stmt = stmt.where(
            MarketingContact.country_code == normalize_country(country_code)
        )
    rows: Iterable[MarketingContact] = session.scalars(stmt).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "business_name",
            "phone",
            "email",
            "website",
            "about_blurb",
            "country_code",
            "city",
            "venue_category",
            "source_url",
            "last_scraped_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.business_name,
                row.phone or "",
                row.email or "",
                row.website or "",
                row.about_blurb or "",
                row.country_code,
                row.city or "",
                row.venue_category or "",
                row.source_url or "",
                row.last_scraped_at.isoformat() if row.last_scraped_at else "",
            ]
        )
    return buf.getvalue()


def count_marketing_contacts(session: Session) -> int:
    return len(session.scalars(select(MarketingContact.id)).all())
