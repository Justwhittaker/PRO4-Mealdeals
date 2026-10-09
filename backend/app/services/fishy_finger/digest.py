"""Sunday ntfy digest for Fishy Finger Sub.

Sent on the existing ntfy topic. Counts are this week's new lead emails
(created since Sunday 08:00 Europe/Dublin), the all-time unsubscribe total,
and the outreach queue still waiting (same rules as the daily drip).

Zone and category percentages are shares of those new lead emails.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.scrapers.zones import SCRAPE_ZONES
from app.services.fishy_finger.constants import FISHY_FINGER_SEGMENT
from app.services.fishy_finger.schedule import DUBLIN, fishy_week_start
from app.services.merchant_outreach import outreach_queue_stats
from app.services.ntfy import send_ntfy

logger = logging.getLogger(__name__)

# Short labels for the ntfy body. Parent ids stay in the database.
_CATEGORY_SHORT: dict[str, str] = {
    "Restaurants, Cafe's & Bistro's": "Restaurants",
    "Food Trucks & Takeaway's": "Takeaways",
    "Wine Farms & Entertainment Venues": "Wine farms",
    "Deli's and Grocers": "Delis",
    "Clubs, Bars & Pubs": "Bars & pubs",
    "Hotels, Resorts & B&B's": "Hotels",
}

_NEW_LEADS = """
SELECT lead_zone, venue_category
FROM marketing_contacts
WHERE source_segment = :segment
  AND email IS NOT NULL
  AND BTRIM(email) <> ''
  AND created_at >= :since
"""

_UNSUBSCRIBED = """
SELECT COUNT(*) FROM marketing_contacts
WHERE outreach_unsubscribed_at IS NOT NULL
"""


def zone_digest_label(zone_id: str | None) -> str:
    key = (zone_id or "").strip().lower()
    if not key:
        return "Unknown"
    meta = SCRAPE_ZONES.get(key) or {}
    label = str(meta.get("label") or key)
    return label.replace(" (large)", "")


def category_digest_label(raw: str | None) -> str:
    text_value = (raw or "").strip()
    if not text_value:
        return "Uncategorized"
    if text_value in _CATEGORY_SHORT:
        return _CATEGORY_SHORT[text_value]
    return text_value


def percentage_breakdown(counts: dict[str, int]) -> list[tuple[str, int, float]]:
    """Shares of ``counts``, largest first. Percentages use one decimal."""
    total = sum(int(value) for value in counts.values())
    ranked = sorted(counts.items(), key=lambda item: (-int(item[1]), item[0]))
    rows: list[tuple[str, int, float]] = []
    for label, count in ranked:
        number = int(count)
        pct = round(100.0 * number / total, 1) if total else 0.0
        rows.append((label, number, pct))
    return rows


def format_fishy_digest(report: dict[str, Any]) -> str:
    """Plain-text ntfy body. ``by_zone`` and ``by_category`` are percentage rows."""
    lines = [
        f"Fishy Finger Sub — week of {report['week_label']}",
        f"Net new lead emails: {report['net_new_lead_emails']}",
        f"Unsubscribed: {report['unsubscribed']}",
        f"Still to email: {report['still_to_email']}",
        "By zone:",
    ]
    zones = report.get("by_zone") or []
    if not zones:
        lines.append("• none")
    for label, count, pct in zones:
        lines.append(f"• {label}: {pct:.0f}% ({count})")
    lines.append("By category:")
    categories = report.get("by_category") or []
    if not categories:
        lines.append("• none")
    for label, count, pct in categories:
        lines.append(f"• {label}: {pct:.0f}% ({count})")
    return "\n".join(lines)


def build_fishy_digest_report(now: datetime | None = None) -> dict[str, Any]:
    """Load this week's lead mix plus the live outreach queue."""
    current = now or datetime.now(DUBLIN)
    start = fishy_week_start(current)
    week_label = start.astimezone(DUBLIN).strftime("%Y-%m-%d")
    engine = create_engine(get_settings().database_url_sync, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        lead_rows = session.execute(
            text(_NEW_LEADS),
            {"segment": FISHY_FINGER_SEGMENT, "since": start},
        ).all()
        unsubscribed = int(session.execute(text(_UNSUBSCRIBED)).scalar_one() or 0)
        pending = outreach_queue_stats(session)["pending_outreach"]

    zone_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for zone_id, category in lead_rows:
        zone_label = zone_digest_label(str(zone_id) if zone_id else "")
        zone_counts[zone_label] = zone_counts.get(zone_label, 0) + 1
        cat_label = category_digest_label(str(category) if category else "")
        category_counts[cat_label] = category_counts.get(cat_label, 0) + 1

    return {
        "week_start": start.isoformat(),
        "week_label": week_label,
        "net_new_lead_emails": len(lead_rows),
        "unsubscribed": unsubscribed,
        "still_to_email": pending,
        "by_zone": percentage_breakdown(zone_counts),
        "by_category": percentage_breakdown(category_counts),
    }


def run_fishy_finger_digest(now: datetime | None = None) -> dict[str, Any]:
    """Build the weekly report and push it to the configured ntfy topic."""
    report = build_fishy_digest_report(now=now)
    body = format_fishy_digest(report)
    notify = send_ntfy(
        "Fishy Finger Sub",
        body,
        priority="default",
        tags="newspaper",
    )
    logger.info(
        "Fishy Finger digest week=%s new=%s queue=%s ntfy=%s",
        report["week_label"],
        report["net_new_lead_emails"],
        report["still_to_email"],
        notify,
    )
    return {"report": report, "body": body, "ntfy": notify}
