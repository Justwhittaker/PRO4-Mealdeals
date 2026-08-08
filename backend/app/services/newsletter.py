"""Newsletter subscribe helpers + Friday weekly specials email builder."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.deal import Deal
from app.models.merchant import Merchant
from app.models.newsletter import NewsletterSubscriber
from app.services.email import send_email

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def new_unsubscribe_token() -> str:
    return secrets.token_urlsafe(32)


def unsubscribe_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/newsletter/unsubscribe?token={quote(token)}"


def resubscribe_url(token: str) -> str:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    return f"{base}/newsletter?resubscribe=1&token={quote(token)}"


def soft_unsubscribe(subscriber: NewsletterSubscriber) -> None:
    """Mark unsubscribed without deleting the row."""
    subscriber.is_subscribed = False
    subscriber.unsubscribed_at = datetime.now(timezone.utc)


def soft_resubscribe(subscriber: NewsletterSubscriber) -> None:
    subscriber.is_subscribed = True
    subscriber.unsubscribed_at = None


def _deal_title(deal: Deal) -> str:
    if deal.translations:
        return deal.translations[0].title
    return f"Deal at {deal.merchant.name if deal.merchant else 'Dine A Deal'}"


def fetch_active_deals_for_location(
    session: Session,
    *,
    country_code: Optional[str],
    city: Optional[str],
    limit: int = 12,
) -> list[Deal]:
    """Prefer location-matched deals; fall back to global active feed."""
    q = (
        select(Deal)
        .where(Deal.is_active.is_(True))
        .where(Deal.deleted_at.is_(None))
        .options(
            selectinload(Deal.merchant).selectinload(Merchant.location),
            selectinload(Deal.translations),
        )
        .order_by(Deal.created_at.desc())
        .limit(limit)
    )
    deals = list(session.scalars(q).all())

    if country_code or city:
        matched: list[Deal] = []
        for deal in deals:
            loc = deal.merchant.location if deal.merchant else None
            if not loc:
                continue
            if country_code and loc.country_code.lower() != country_code.lower():
                continue
            if city and loc.city.lower().replace(" ", "-") != city.lower().replace(
                " ", "-"
            ):
                continue
            matched.append(deal)
        if matched:
            return matched[:limit]
    return deals[:limit]


def build_weekly_email(
    subscriber: NewsletterSubscriber,
    deals: list[Deal],
) -> tuple[str, str, str]:
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    unsub = unsubscribe_url(subscriber.unsubscribe_token)
    first = subscriber.name.split()[0] if subscriber.name else "there"

    subject = f"Dine A Deal — this week's specials in {subscriber.location}"

    lines = [
        f"Hi {first},",
        "",
        f"Here are this week's dining deals for {subscriber.location}:",
        "",
    ]
    html_items: list[str] = []

    if not deals:
        lines.append("No active deals right now — check back soon on the site.")
        html_items.append(
            "<p>No active deals right now — check back soon on the site.</p>"
        )
    else:
        for deal in deals:
            title = _deal_title(deal)
            price = deal.deal_price
            currency = deal.currency_code
            merchant = deal.merchant.name if deal.merchant else "Restaurant"
            loc = deal.merchant.location if deal.merchant else None
            country = (loc.country_code if loc else "uk").lower()
            city_slug = (loc.city if loc else "london").lower().replace(" ", "-")
            href = f"{base}/{country}/{city_slug}/deals/{deal.id}"
            price_s = f"{currency} {Decimal(price):.2f}"
            lines.append(f"• {title} — {merchant} — {price_s}")
            lines.append(f"  {href}")
            lines.append("")
            html_items.append(
                f'<li style="margin:0 0 12px">'
                f'<a href="{href}" style="color:#7a1f2b;font-weight:600">'
                f"{title}</a>"
                f"<br/><span style=\"color:#444\">{merchant} · {price_s}</span>"
                f"</li>"
            )

    lines.extend(
        [
            "—",
            "You're receiving this because you signed up for Weekly Specials.",
            f"Unsubscribe (keeps your details on file): {unsub}",
            "",
            f"Browse all deals: {base}",
        ]
    )
    text_body = "\n".join(lines)

    html_body = f"""<!DOCTYPE html>
<html><body style="font-family:Georgia,serif;color:#1a1a1a;max-width:560px;margin:0 auto;padding:24px">
  <h1 style="font-family:Arial,sans-serif;color:#7a1f2b;font-size:22px;text-transform:uppercase;letter-spacing:0.04em">
    Dine A Deal
  </h1>
  <p>Hi {first},</p>
  <p>Here are this week's dining deals for <strong>{subscriber.location}</strong>:</p>
  <ul style="padding-left:18px">{"".join(html_items)}</ul>
  <p style="margin-top:28px;font-size:13px;color:#666">
    You're receiving this because you signed up for Weekly Specials every Friday.
  </p>
  <p style="font-size:13px">
    <a href="{unsub}">Unsubscribe</a>
    — we'll stop emails but keep your details on file so you can subscribe again anytime.
  </p>
  <p style="font-size:13px"><a href="{base}">Browse Dine A Deal</a></p>
</body></html>"""

    return subject, text_body, html_body


def send_weekly_special_to_subscriber(
    session: Session,
    subscriber: NewsletterSubscriber,
) -> dict[str, Any]:
    if not subscriber.is_subscribed:
        return {"email": subscriber.email, "skipped": True, "reason": "unsubscribed"}

    deals = fetch_active_deals_for_location(
        session,
        country_code=subscriber.country_code,
        city=subscriber.city,
    )
    subject, text_body, html_body = build_weekly_email(subscriber, deals)
    ok = send_email(
        to_email=subscriber.email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
    if ok:
        subscriber.last_emailed_at = datetime.now(timezone.utc)
        session.commit()
    return {
        "email": subscriber.email,
        "sent": ok,
        "deal_count": len(deals),
    }
