"""Monthly outreach to scraped hospitality businesses (marketing_contacts)."""

from __future__ import annotations

import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlparse

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.deal import Deal
from app.models.location import Location
from app.models.marketing_contact import MarketingContact
from app.models.merchant import Merchant
from app.services.deal_link import normalize_outbound_url
from app.services.email import is_email_configured, send_email
from app.services.ingest import normalize_city, normalize_country
from app.services.marketing_contacts import _clean_email

logger = logging.getLogger(__name__)

ABOUT_US_BLURB = (
    "We're all about the thrill of a great deal — hunting down tasty savings near you, "
    "and giving hotels, businesses, and grocers a cheerful, flat-rate stage to shout "
    "about their offers (no voucher cut, allowing businesses to keep all their earnings)."
)

# Aligned with GET /api/v1/scrapers/plans/priority (PlanInfo).
MERCHANT_OFFER_BULLETS: tuple[tuple[str, str], ...] = (
    (
        "Free to join",
        "Create your merchant profile and publish deals at no cost.",
    ),
    (
        "Priority hero placement",
        "Get your first month free to explore Priority and see the impact — 3 hero slots "
        "that rank above scraped listings in city feeds, then a flat monthly rate "
        "(card on file; one free month per eligible business).",
    ),
    (
        "Weekly newsletter",
        "Reach diners who opted in for dining specials in their city every Friday.",
    ),
    (
        "Keep what you earn",
        "No commission and no voucher cut — unlike voucher sites, you keep what your "
        "customers pay you.",
    ),
)

_SKIP_EMAIL_RE = re.compile(
    r"^(noreply|no-reply|donotreply|mailer-daemon|postmaster|admin|webmaster|"
    r"support|help|info@example|test@)",
    re.I,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def outreach_unsubscribe_url(token: str) -> str:
    settings = get_settings()
    base = settings.public_api_base_url.rstrip("/")
    return f"{base}/api/v1/marketing/outreach/unsubscribe?token={quote(token)}"


def merchant_dashboard_url() -> str:
    settings = get_settings()
    return f"{settings.frontend_base_url.rstrip('/')}/dashboard"


def _contact_greeting(contact: MarketingContact) -> str:
    name = (contact.business_name or "").strip()
    if not name:
        return "there"
    first = name.split()[0]
    if len(first) > 1 and first[0].isupper():
        return first
    return name


def ensure_outreach_token(contact: MarketingContact) -> str:
    if contact.outreach_unsubscribe_token:
        return contact.outreach_unsubscribe_token
    token = secrets.token_urlsafe(32)
    contact.outreach_unsubscribe_token = token
    return token


def _website_host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url.strip()).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:  # noqa: BLE001
        return None


def _load_registered_merchant_emails(session: Session) -> set[str]:
    rows = session.scalars(
        select(Merchant.email).where(Merchant.email.is_not(None))
    ).all()
    return {email.strip().lower() for email in rows if email and email.strip()}


def _load_registered_merchant_domains(session: Session) -> set[str]:
    rows = session.scalars(
        select(Merchant.website).where(Merchant.email.is_not(None))
    ).all()
    domains: set[str] = set()
    for website in rows:
        host = _website_host(website)
        if host:
            domains.add(host)
    return domains


def is_existing_merchant_contact(
    contact: MarketingContact,
    *,
    merchant_emails: set[str],
    merchant_domains: set[str],
) -> bool:
    """Skip businesses that already registered on Dine A Deal."""
    email = _clean_email(contact.email)
    if email and email in merchant_emails:
        return True
    contact_host = _website_host(contact.website)
    if contact_host and contact_host in merchant_domains:
        return True
    return False


def exclude_existing_merchant_contact(session: Session, contact: MarketingContact) -> None:
    contact.outreach_excluded_at = _utcnow()
    session.commit()


def is_outreach_eligible_email(email: str | None) -> bool:
    cleaned = _clean_email(email)
    if not cleaned:
        return False
    local = cleaned.split("@", 1)[0]
    if _SKIP_EMAIL_RE.match(local):
        return False
    return True


def _dineadeal_host(base: str) -> str:
    return urlparse(base).netloc.lower().removeprefix("www.")


def _is_dineadeal_deal_url(url: str, base: str) -> bool:
    """True when URL is a public deal page on our site (not /about or city feed)."""
    try:
        parsed = urlparse(url.strip())
        host = parsed.netloc.lower().removeprefix("www.")
        if host != _dineadeal_host(base):
            return False
        parts = [part for part in parsed.path.split("/") if part]
        return len(parts) >= 4 and parts[2] == "deals"
    except Exception:  # noqa: BLE001
        return False


def _deal_public_url(deal: Deal, base: str) -> str | None:
    loc = deal.merchant.location if deal.merchant else None
    if loc is None:
        return None
    country = loc.country_code.lower()
    city_slug = loc.city.lower().replace(" ", "-")
    return f"{base}/{country}/{city_slug}/deals/{deal.id}"


def _city_deals_url(contact: MarketingContact, base: str) -> str | None:
    if not contact.country_code or not contact.city:
        return None
    country = normalize_country(contact.country_code).lower()
    city_slug = normalize_city(contact.city).lower().replace(" ", "-")
    return f"{base}/{country}/{city_slug}/deals"


def _deal_lookup_options() -> tuple[Any, ...]:
    return (
        selectinload(Deal.merchant).selectinload(Merchant.location),
    )


def _find_deal_for_contact(session: Session, contact: MarketingContact) -> Deal | None:
    """Best-effort match from marketing contact → scraped deal on Dine A Deal."""
    loaders = _deal_lookup_options()
    country = normalize_country(contact.country_code)
    city_name = normalize_city(contact.city) if contact.city else None

    if contact.source_url:
        deal = session.scalar(
            select(Deal)
            .where(Deal.scraped_raw_url == contact.source_url)
            .where(Deal.deleted_at.is_(None))
            .options(*loaders)
            .limit(1)
        )
        if deal is not None:
            return deal

        normalized_source = normalize_outbound_url(contact.source_url)
        if normalized_source:
            deal = session.scalar(
                select(Deal)
                .where(Deal.scraped_raw_url == normalized_source)
                .where(Deal.deleted_at.is_(None))
                .options(*loaders)
                .limit(1)
            )
            if deal is not None:
                return deal

        source_root = contact.source_url.split("?", 1)[0]
        deal = session.scalar(
            select(Deal)
            .where(Deal.scraped_raw_url.like(f"{source_root}%"))
            .where(Deal.deleted_at.is_(None))
            .options(*loaders)
            .order_by(Deal.created_at.desc())
            .limit(1)
        )
        if deal is not None:
            return deal

    if contact.website:
        stmt = (
            select(Deal)
            .join(Merchant, Deal.merchant_id == Merchant.id)
            .join(Location, Merchant.location_id == Location.id)
            .where(Deal.deleted_at.is_(None))
            .where(Merchant.website == contact.website)
            .where(Location.country_code == country)
            .options(*loaders)
            .order_by(Deal.created_at.desc())
            .limit(1)
        )
        if city_name:
            stmt = stmt.where(func.lower(Location.city) == city_name.lower())
        deal = session.scalar(stmt)
        if deal is not None:
            return deal

    business_name = (contact.business_name or "").strip()
    if business_name:
        stmt = (
            select(Deal)
            .join(Merchant, Deal.merchant_id == Merchant.id)
            .join(Location, Merchant.location_id == Location.id)
            .where(Deal.deleted_at.is_(None))
            .where(func.lower(Merchant.name) == business_name.lower())
            .where(Location.country_code == country)
            .options(*loaders)
            .order_by(Deal.created_at.desc())
            .limit(1)
        )
        if city_name:
            stmt = stmt.where(func.lower(Location.city) == city_name.lower())
        deal = session.scalar(stmt)
        if deal is not None:
            return deal

    return None


def resolve_dineadeal_listing_url(
    session: Session,
    contact: MarketingContact,
) -> str | None:
    """Public Dine A Deal URL for this business (deal page, else city feed)."""
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")

    if contact.source_url and _is_dineadeal_deal_url(contact.source_url, base):
        return contact.source_url

    deal = _find_deal_for_contact(session, contact)
    if deal is not None:
        return _deal_public_url(deal, base)

    return _city_deals_url(contact, base)


def build_merchant_outreach_email(
    contact: MarketingContact,
    *,
    unsubscribe_token: str,
    listing_url: str | None = None,
) -> tuple[str, str, str]:
    """Subject, plain text, HTML for one business outreach message."""
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    greeting = _contact_greeting(contact)
    city = contact.city or "your area"
    country = contact.country_code.upper()
    unsub = outreach_unsubscribe_url(unsubscribe_token)
    dashboard = merchant_dashboard_url()

    subject = (
        f"We found your {city} deal on Dine A Deal — keep 100% of what you earn"
    )

    deal_hint = ""
    if listing_url:
        deal_hint = f"\nView your listing on Dine A Deal: {listing_url}\n"

    lines = [
        f"Hello {greeting},",
        "",
        f"Did you know Dine A Deal already found your business in {city}, {country}? "
        "We'd love to send more hungry locals to your site.",
        deal_hint.rstrip(),
        "",
        "About us",
        "",
        ABOUT_US_BLURB,
        "",
        "What that means for you:",
        "",
        *[
            f"• {title} — {detail}"
            for title, detail in MERCHANT_OFFER_BULLETS
        ],
        "",
        f"Claim your listing: {dashboard}",
        f"About Dine A Deal: {base}/about",
        f"Browse deals: {base}",
        "",
        "Kindest regards,",
        "The DineADeal team",
        "",
        "—",
        "You're receiving this because we found public contact details while indexing "
        "hospitality deals.",
        f"Opt out of merchant outreach: {unsub}",
    ]
    text_body = "\n".join(line for line in lines if line is not None)

    logo_mark = f"{base}/logo-dineadeal.png"
    logo_wordmark = f"{base}/logo-wordmark.png"
    listing_link_html = ""
    if listing_url:
        listing_link_html = (
            f'<p><a href="{listing_url}" style="color:#7a1f2b;font-weight:600">'
            "View your listing on Dine A Deal</a></p>"
        )

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;color:#1a1a1a;max-width:560px;margin:0 auto;padding:24px">
  <p style="margin:0 0 24px">
    <a href="{base}" style="text-decoration:none;display:inline-block">
      <img src="{logo_mark}" alt="" width="48" height="48" style="display:inline-block;vertical-align:middle;border:0" />
      <img src="{logo_wordmark}" alt="Dine A Deal" width="180" height="48" style="display:inline-block;vertical-align:middle;border:0;margin-left:8px" />
    </a>
  </p>
  <p>Hello {greeting},</p>
  <p>
    Did you know <strong>Dine A Deal</strong> already found your business in
    <strong>{city}, {country}</strong>? We'd love to send more hungry locals to your site.
  </p>
  {listing_link_html}
  <h2 style="font-family:Arial,sans-serif;color:#7a1f2b;font-size:16px;margin-top:24px">
    About us
  </h2>
  <p style="line-height:1.6;color:#333">{ABOUT_US_BLURB}</p>
  <h2 style="font-family:Arial,sans-serif;color:#7a1f2b;font-size:16px;margin-top:24px">
    What that means for you
  </h2>
  <ul style="padding-left:18px;line-height:1.6">
    {
        "".join(
            f"<li><strong>{title}</strong> — {detail}</li>"
            for title, detail in MERCHANT_OFFER_BULLETS
        )
    }
  </ul>
  <p style="margin-top:24px">
    <a href="{dashboard}" style="display:inline-block;background:#7a1f2b;color:#fff;padding:12px 20px;text-decoration:none;border-radius:6px;font-family:Arial,sans-serif;font-weight:600">
      Claim your merchant listing
    </a>
  </p>
  <p style="font-size:14px;margin-top:20px">
    <a href="{base}/about">About Dine A Deal</a> ·
    <a href="{base}">Browse deals</a>
  </p>
  <p style="margin-top:28px;line-height:1.5">
    Kindest regards,<br />
    <strong>The DineADeal team</strong>
  </p>
  <p style="margin-top:28px;font-size:12px;color:#666">
    Public contact details were found while indexing hospitality deals.
    <a href="{unsub}">Opt out of merchant outreach</a>.
  </p>
</body></html>"""

    return subject, text_body, html_body


def send_outreach_to_contact(
    session: Session,
    contact: MarketingContact,
) -> dict[str, Any]:
    if contact.outreach_unsubscribed_at is not None:
        return {"email": contact.email, "skipped": True, "reason": "unsubscribed"}
    if not is_outreach_eligible_email(contact.email):
        return {"email": contact.email, "skipped": True, "reason": "no_valid_email"}

    token = ensure_outreach_token(contact)
    listing_url = resolve_dineadeal_listing_url(session, contact)
    subject, text_body, html_body = build_merchant_outreach_email(
        contact,
        unsubscribe_token=token,
        listing_url=listing_url,
    )
    settings = get_settings()
    ok = send_email(
        to_email=contact.email,  # type: ignore[arg-type]
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        reply_to=settings.merchant_outreach_reply_to,
    )
    if ok:
        contact.last_outreach_sent_at = _utcnow()
        session.commit()
    return {
        "email": contact.email,
        "business_name": contact.business_name,
        "sent": ok,
    }


def fetch_outreach_batch(
    session: Session,
    *,
    persist_exclusions: bool = True,
) -> list[MarketingContact]:
    """Contacts with email, not unsubscribed/excluded, not emailed recently."""
    settings = get_settings()
    min_days = settings.merchant_outreach_min_days
    max_rows = settings.merchant_outreach_max_per_run
    cutoff = _utcnow() - timedelta(days=min_days)
    merchant_emails = _load_registered_merchant_emails(session)
    merchant_domains = _load_registered_merchant_domains(session)

    stmt = (
        select(MarketingContact)
        .where(MarketingContact.email.is_not(None))
        .where(MarketingContact.email != "")
        .where(MarketingContact.outreach_unsubscribed_at.is_(None))
        .where(MarketingContact.outreach_excluded_at.is_(None))
        .where(
            or_(
                MarketingContact.last_outreach_sent_at.is_(None),
                MarketingContact.last_outreach_sent_at < cutoff,
            )
        )
        .order_by(
            MarketingContact.last_outreach_sent_at.asc().nullsfirst(),
            MarketingContact.last_scraped_at.desc(),
        )
        .limit(max_rows * 5)
    )
    rows = list(session.scalars(stmt).all())
    eligible: list[MarketingContact] = []
    for row in rows:
        if not is_outreach_eligible_email(row.email):
            continue
        if is_existing_merchant_contact(
            row,
            merchant_emails=merchant_emails,
            merchant_domains=merchant_domains,
        ):
            if persist_exclusions:
                exclude_existing_merchant_contact(session, row)
            continue
        eligible.append(row)
        if len(eligible) >= max_rows:
            break
    return eligible


def outreach_queue_stats(session: Session) -> dict[str, int]:
    """Counts for monitoring backlog vs Resend quotas."""
    settings = get_settings()
    cutoff = _utcnow() - timedelta(days=settings.merchant_outreach_min_days)
    with_email = int(
        session.scalar(
            select(func.count())
            .select_from(MarketingContact)
            .where(MarketingContact.email.is_not(None))
            .where(MarketingContact.email != "")
        )
        or 0
    )
    pending = int(
        session.scalar(
            select(func.count())
            .select_from(MarketingContact)
            .where(MarketingContact.email.is_not(None))
            .where(MarketingContact.email != "")
            .where(MarketingContact.outreach_unsubscribed_at.is_(None))
            .where(MarketingContact.outreach_excluded_at.is_(None))
            .where(
                or_(
                    MarketingContact.last_outreach_sent_at.is_(None),
                    MarketingContact.last_outreach_sent_at < cutoff,
                )
            )
        )
        or 0
    )
    excluded = int(
        session.scalar(
            select(func.count())
            .select_from(MarketingContact)
            .where(MarketingContact.outreach_excluded_at.is_not(None))
        )
        or 0
    )
    return {
        "with_email": with_email,
        "pending_outreach": pending,
        "excluded_existing_merchants": excluded,
        "max_per_run": settings.merchant_outreach_max_per_run,
    }


def send_merchant_outreach_batch(session: Session) -> dict[str, int]:
    """Send monthly merchant outreach to the next eligible batch."""
    settings = get_settings()
    if not settings.merchant_outreach_enabled:
        logger.info("Merchant outreach disabled (MERCHANT_OUTREACH_ENABLED=false)")
        return {"sent": 0, "skipped": 0, "failed": 0, "disabled": 1}

    if not is_email_configured():
        logger.error("Merchant outreach skipped — email not configured (RESEND_API_KEY)")
        return {"sent": 0, "skipped": 0, "failed": 0, "error": 1}

    sent = 0
    skipped = 0
    failed = 0
    excluded = 0
    delay_sec = settings.merchant_outreach_send_delay_ms / 1000.0

    contacts = fetch_outreach_batch(session)
    stats_before = outreach_queue_stats(session)
    excluded = stats_before.get("excluded_existing_merchants", 0)

    for index, contact in enumerate(contacts):
        if index > 0 and delay_sec > 0:
            time.sleep(delay_sec)
        result = send_outreach_to_contact(session, contact)
        if result.get("skipped"):
            skipped += 1
        elif result.get("sent"):
            sent += 1
        else:
            failed += 1

    stats_after = outreach_queue_stats(session)
    summary = {
        "sent": sent,
        "skipped": skipped,
        "failed": failed,
        "excluded_existing_merchants": stats_after.get("excluded_existing_merchants", excluded),
        "pending_outreach": stats_after.get("pending_outreach", 0),
        "with_email": stats_after.get("with_email", 0),
    }
    logger.info("Merchant outreach batch complete: %s", summary)
    return summary


def unsubscribe_merchant_outreach(session: Session, token: str) -> bool:
    row = session.execute(
        select(MarketingContact)
        .where(MarketingContact.outreach_unsubscribe_token == token.strip())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return False
    row.outreach_unsubscribed_at = _utcnow()
    session.commit()
    return True
