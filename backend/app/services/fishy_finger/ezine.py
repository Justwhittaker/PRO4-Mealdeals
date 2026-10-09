"""Ezine-style outreach for Fishy Finger Sub leads.

Copy states only what the product already publishes:

- DineADeal lists dining and drink deals.
- Reach is the live active-deal count from ``GET /api/v1/scrapers/metrics``
  (the same ``active_deals`` figure as the public site header). When that
  count is unavailable the sentence does not invent a number.
- Listing is free and there is no commission, matching the existing merchant
  outreach bullets.
- Priority matches ``PlanInfo`` (``GET /api/v1/scrapers/plans/priority``):
  €20 for 3 months with 3 hero slots, then €20 a month with the same 3 slots.
- The Friday newsletter goes to diners who already opted in.

No testimonials and no audience figures beyond the live deal count.
"""

from __future__ import annotations

import html
import logging
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.models.deal import Deal
from app.models.marketing_contact import MarketingContact

logger = logging.getLogger(__name__)

# Public Priority plan (PlanInfo on GET /api/v1/scrapers/plans/priority).
# test_fishy_finger_sub checks these against that model so the email cannot drift.
PRIORITY_INTRO_PRICE_EUR = 20
PRIORITY_INTRO_MONTHS = 3
PRIORITY_SLOTS = 3
PRIORITY_RECURRING_PRICE_EUR = 20


def active_deals_sentence(count: int | None, *, business_name: str, city: str) -> str:
    """Reach line. Omits a number when metrics did not answer."""
    place = f"{business_name} in {city} is not listed yet."
    if count is None:
        return f"Diners browse live deals on DineADeal. {place}"
    noun = "deal" if count == 1 else "deals"
    return f"Diners browse {count:,} live {noun} on DineADeal. {place}"


def load_live_active_deals(session: Session) -> int | None:
    """Active deals from the public metrics endpoint, otherwise the same DB count.

    Returns None only when both the metrics request and the database count fail.
    """
    settings = get_settings()
    api_base = (settings.public_api_base_url or "").rstrip("/")
    if api_base:
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(f"{api_base}/api/v1/scrapers/metrics")
            if response.status_code == 200:
                payload: Any = response.json()
                if isinstance(payload, dict) and "active_deals" in payload:
                    return int(payload["active_deals"])
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
            logger.info("Fishy ezine metrics lookup failed: %s", exc)
    try:
        count = session.scalar(
            select(func.count()).select_from(Deal).where(Deal.is_active.is_(True))
        )
    except Exception as exc:  # noqa: BLE001
        reraise_if_fatal(exc)
        logger.info("Fishy ezine active-deal query failed: %s", exc)
        return None
    return int(count or 0)


def _greeting(contact: MarketingContact) -> str:
    name = (contact.business_name or "").strip()
    if not name:
        return "there"
    first = name.split()[0]
    if len(first) > 1 and first[0].isupper():
        return first
    return name


def _subscription_paragraph() -> str:
    intro = int(PRIORITY_INTRO_PRICE_EUR)
    months = int(PRIORITY_INTRO_MONTHS)
    slots = int(PRIORITY_SLOTS)
    recurring = int(PRIORITY_RECURRING_PRICE_EUR)
    return (
        "A listing is free. You publish the offer, diners come to you, and you "
        "keep what you earn — no commission and no voucher cut. Priority placement "
        f"is optional: €{intro} for {months} months with {slots} hero slots that "
        f"rank above scraped listings, then €{recurring} a month with the same "
        f"{slots} slots. Your deal can also go in the Friday newsletter to diners "
        "who asked for specials in their city."
    )


def build_fishy_ezine(
    contact: MarketingContact,
    *,
    unsubscribe_url: str,
    dashboard_url: str,
    active_deals: int | None,
) -> tuple[str, str, str]:
    """Subject, plain text, and mobile-friendly HTML for one lead."""
    settings = get_settings()
    base = settings.frontend_base_url.rstrip("/")
    greeting = _greeting(contact)
    business = (contact.business_name or "your business").strip()
    city = (contact.city or "your area").strip()
    reach = active_deals_sentence(active_deals, business_name=business, city=city)
    offer = _subscription_paragraph()
    subject = f"List {business} on DineADeal"

    text_body = "\n".join(
        [
            f"Hello {greeting},",
            "",
            "DineADeal is where diners look for offers at restaurants, cafés, bars, "
            "pubs, wine farms and other places to eat and drink.",
            "",
            reach,
            "",
            offer,
            "",
            f"List your business: {dashboard_url}",
            "",
            "Kindest regards,",
            "The DineADeal team",
            "",
            "—",
            f"You're receiving this because a public contact for {business} was found "
            "while looking for independent places to eat and drink that are not yet "
            "on DineADeal.",
            f"Unsubscribe: {unsubscribe_url}",
        ]
    )

    esc_greeting = html.escape(greeting)
    esc_business = html.escape(business)
    esc_reach = html.escape(reach)
    esc_offer = html.escape(offer)
    esc_unsub = html.escape(unsubscribe_url, quote=True)
    esc_dashboard = html.escape(dashboard_url, quote=True)
    esc_base = html.escape(base, quote=True)
    logo_mark = f"{base}/logo-dineadeal.png"
    logo_wordmark = f"{base}/logo-wordmark.png"

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:#f6f1ea;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#f6f1ea;">
    {esc_reach}
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f1ea;">
    <tr>
      <td align="center" style="padding:16px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;">
          <tr>
            <td style="padding:24px 20px;font-family:Georgia,serif;font-size:16px;line-height:1.5;color:#1a1a1a;">
              <p style="margin:0 0 20px;">
                <a href="{esc_base}" style="text-decoration:none;">
                  <img src="{html.escape(logo_mark, quote=True)}" alt="" width="48" height="48" style="display:inline-block;vertical-align:middle;border:0;max-width:48px;height:auto;">
                  <img src="{html.escape(logo_wordmark, quote=True)}" alt="DineADeal" width="180" height="48" style="display:inline-block;vertical-align:middle;border:0;margin-left:8px;max-width:180px;height:auto;">
                </a>
              </p>
              <p style="margin:0 0 16px;">Hello {esc_greeting},</p>
              <p style="margin:0 0 16px;">DineADeal is where diners look for offers at restaurants, cafés, bars, pubs, wine farms and other places to eat and drink.</p>
              <p style="margin:0 0 16px;">{esc_reach}</p>
              <p style="margin:0 0 20px;">{esc_offer}</p>
              <p style="margin:0 0 24px;">
                <a href="{esc_dashboard}" style="display:block;max-width:280px;background:#7a1f2b;color:#ffffff;padding:14px 18px;text-decoration:none;border-radius:8px;font-family:Arial,sans-serif;font-size:16px;font-weight:700;text-align:center;">List your business</a>
              </p>
              <p style="margin:0 0 8px;">Kindest regards,<br><strong>The DineADeal team</strong></p>
              <p style="margin:24px 0 0;font-size:13px;line-height:1.45;color:#555555;">
                You're receiving this because a public contact for {esc_business} was found while looking for independent places to eat and drink that are not yet on DineADeal.
                <a href="{esc_unsub}" style="color:#7a1f2b;">Unsubscribe</a>.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return subject, text_body, html_body
