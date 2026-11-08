"""Sunday ntfy digest for Fishy Finger Sub.

Sent on the existing ntfy topic. Counts are this week's new lead emails
(created since Sunday 08:00 Europe/Dublin), the all-time unsubscribe total,
and the outreach queue still waiting (same rules as the daily drip).

Zone and category percentages are shares of those new lead emails.
The no-specials lines are the count and share of new leads with
has_site_specials false, by zone, category, and EU / NA / other.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.scrapers.zones import SCRAPE_ZONES
from app.services.new_business_outreach.constants import FISHY_FINGER_SEGMENT
from app.services.new_business_outreach.db import open_session
from app.services.new_business_outreach.schedule import DUBLIN, last_weekly_slot, lead_region
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
SELECT lead_zone, venue_category, has_site_specials
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


def _share(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * count / total, 1)


def no_specials_breakdown(
    rows: list[tuple[object, object, object]],
) -> dict[str, Any]:
    """Count has_site_specials false, and that count's share of each bucket."""
    total = len(rows)
    flagged = 0
    zone_total: dict[str, int] = {}
    zone_flagged: dict[str, int] = {}
    category_total: dict[str, int] = {}
    category_flagged: dict[str, int] = {}
    region_total = {"EU": 0, "NA": 0, "Other": 0}
    region_flagged = {"EU": 0, "NA": 0, "Other": 0}
    for zone_id, category, flag in rows:
        is_flagged = flag is False
        if is_flagged:
            flagged += 1
        zone_label = zone_digest_label(str(zone_id) if zone_id else "")
        zone_total[zone_label] = zone_total.get(zone_label, 0) + 1
        if is_flagged:
            zone_flagged[zone_label] = zone_flagged.get(zone_label, 0) + 1
        cat_label = category_digest_label(str(category) if category else "")
        category_total[cat_label] = category_total.get(cat_label, 0) + 1
        if is_flagged:
            category_flagged[cat_label] = category_flagged.get(cat_label, 0) + 1
        region = lead_region(str(zone_id) if zone_id else "")
        region_total[region] = region_total.get(region, 0) + 1
        if is_flagged:
            region_flagged[region] = region_flagged.get(region, 0) + 1

    def _rows(
        totals: dict[str, int],
        flags: dict[str, int],
    ) -> list[tuple[str, int, int, float]]:
        ranked = sorted(totals, key=lambda label: (-flags.get(label, 0), label))
        built: list[tuple[str, int, int, float]] = []
        for label in ranked:
            bucket = totals[label]
            count = flags.get(label, 0)
            built.append((label, count, bucket, _share(count, bucket)))
        return built

    region_rows = [
        (
            label,
            region_flagged.get(label, 0),
            region_total.get(label, 0),
            _share(region_flagged.get(label, 0), region_total.get(label, 0)),
        )
        for label in ("EU", "NA", "Other")
    ]
    return {
        "no_specials": flagged,
        "no_specials_pct": _share(flagged, total),
        "no_specials_by_zone": _rows(zone_total, zone_flagged),
        "no_specials_by_category": _rows(category_total, category_flagged),
        "no_specials_by_region": region_rows,
    }


def _share_block(
    title: str,
    rows: list[tuple[str, int, int, float]] | None,
) -> list[str]:
    lines = [title]
    if not rows:
        lines.append("• none")
        return lines
    for label, count, total, pct in rows:
        lines.append(f"• {label}: {count} ({pct:.0f}% of {total})")
    return lines


def format_fishy_digest(report: dict[str, Any]) -> str:
    """Plain-text ntfy body, including the no-specials share of new leads."""
    new_leads = int(report.get("net_new_lead_emails") or 0)
    no_specials = int(report.get("no_specials") or 0)
    pct = report.get("no_specials_pct")
    if pct is None:
        pct = _share(no_specials, new_leads)
    outreach_line = (
        "Fishy outreach: enabled"
        if report.get("fishy_outreach_enabled")
        else "Fishy outreach: disabled"
    )
    lines = [
        f"Fishy Finger Sub — week of {report['week_label']}",
        outreach_line,
        f"Net new lead emails: {new_leads}",
        f"No specials: {no_specials} ({float(pct):.0f}% of {new_leads} new leads)",
        f"Unsubscribed: {report['unsubscribed']}",
        f"Still to email: {report['still_to_email']}",
        "By zone:",
    ]
    zones = report.get("by_zone") or []
    if not zones:
        lines.append("• none")
    for label, count, pct_zone in zones:
        lines.append(f"• {label}: {pct_zone:.0f}% ({count})")
    lines.append("By category:")
    categories = report.get("by_category") or []
    if not categories:
        lines.append("• none")
    for label, count, pct_category in categories:
        lines.append(f"• {label}: {pct_category:.0f}% ({count})")
    lines.extend(_share_block("No specials by zone:", report.get("no_specials_by_zone")))
    lines.extend(
        _share_block("No specials by category:", report.get("no_specials_by_category"))
    )
    lines.extend(_share_block("No specials by region:", report.get("no_specials_by_region")))
    return "\n".join(lines)


def build_fishy_digest_report(now: datetime | None = None) -> dict[str, Any]:
    """Load this week's lead mix plus the live outreach queue."""
    current = now or datetime.now(DUBLIN)
    start = last_weekly_slot(
        current, weekday=6, hour=0, minute=0
    ).astimezone(timezone.utc)
    week_label = start.astimezone(DUBLIN).strftime("%Y-%m-%d")
    engine, session_factory = open_session()
    try:
        with session_factory() as session:
            lead_rows = session.execute(
                text(_NEW_LEADS),
                {"segment": FISHY_FINGER_SEGMENT, "since": start},
            ).all()
            unsubscribed = int(session.execute(text(_UNSUBSCRIBED)).scalar_one() or 0)
            pending = outreach_queue_stats(session)["pending_outreach"]
    finally:
        engine.dispose()

    zone_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for zone_id, category, _flag in lead_rows:
        zone_label = zone_digest_label(str(zone_id) if zone_id else "")
        zone_counts[zone_label] = zone_counts.get(zone_label, 0) + 1
        cat_label = category_digest_label(str(category) if category else "")
        category_counts[cat_label] = category_counts.get(cat_label, 0) + 1

    return {
        "week_start": start.isoformat(),
        "week_label": week_label,
        "net_new_lead_emails": len(lead_rows),
        "fishy_outreach_enabled": get_settings().fishy_outreach_enabled,
        "unsubscribed": unsubscribed,
        "still_to_email": pending,
        "by_zone": percentage_breakdown(zone_counts),
        "by_category": percentage_breakdown(category_counts),
        **no_specials_breakdown(list(lead_rows)),
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


def format_outreach_digest(report: dict[str, Any]) -> str:
    """Short ntfy body for one weekly New Business Outreach run."""
    outreach = (
        "Outreach: enabled"
        if report.get("outreach_enabled")
        else "Outreach: disabled"
    )
    resume = (
        "Planet pass finished. Next week starts at the first European tile."
        if report.get("wrapped")
        else f"Resumes at tile {report.get('next_tile_index', 0)} next week."
    )
    lines = [
        f"New Business Outreach — week of {report.get('week_label', '')}",
        outreach,
        (
            f"Tiles this run: {report.get('tiles_run', 0)} of "
            f"{report.get('tiles_total', 0)} (cycle {report.get('cycle', 1)})"
        ),
        resume,
        f"Found: {report.get('found', 0)}",
        f"With email: {report.get('with_email', 0)}",
        f"Excluded already on site: {report.get('excluded_on_site', 0)}",
        f"Failed tiles: {report.get('failed', 0)}",
        (
            f"Lead storage: {report.get('storage_mb', 0)} MB / "
            f"{report.get('storage_cap_mb', 100)} MB"
        ),
        "By zone:",
    ]
    zones = report.get("by_zone") or {}
    if not zones:
        lines.append("• none")
    for label, counts in sorted(zones.items()):
        lines.append(
            f"• {zone_digest_label(label)}: found {counts.get('found', 0)}, "
            f"email {counts.get('with_email', 0)}, excluded {counts.get('excluded', 0)}"
        )
    lines.append("By type:")
    types = report.get("by_type") or {}
    if not types:
        lines.append("• none")
    for label, counts in sorted(types.items()):
        lines.append(
            f"• {category_digest_label(label)}: found {counts.get('found', 0)}, "
            f"email {counts.get('with_email', 0)}, excluded {counts.get('excluded', 0)}"
        )
    reasons = report.get("reasons") or {}
    if reasons:
        lines.append("Excluded because:")
        for reason, count in sorted(reasons.items()):
            lines.append(f"• {reason}: {count}")
    failed = report.get("failed_tiles") or []
    if failed:
        lines.append("Failed: " + ", ".join(str(item) for item in failed[:12]))
    if report.get("yielded"):
        lines.append("Stopped before 07:00 Europe/Dublin so zone scrapes keep priority.")
    if report.get("storage_stopped"):
        lines.append("Stopped inserting because lead storage reached the cap.")
    fetches = report.get("website_fetches")
    deferred = report.get("website_deferred")
    if fetches is not None:
        lines.append(f"Website fetches: {fetches} (deferred {deferred or 0})")
    own_ads = "on" if report.get("skip_own_ads") else "off"
    lines.append(f"Own-ads filter: {own_ads}")
    sheet = report.get("sheet") or {}
    if sheet.get("skipped"):
        lines.append(f"Sheet: skipped ({sheet.get('reason', 'unconfigured')})")
    elif sheet.get("ok"):
        lines.append(f"Sheet: {sheet.get('rows', 0)} rows ({sheet.get('mode', 'tab')})")
    else:
        lines.append("Sheet: failed")
    return "\n".join(lines)


def send_outreach_digest(body: str) -> dict[str, Any]:
    """Post the weekly summary. Does not send email."""
    notify = send_ntfy(
        "New Business Outreach",
        body,
        priority="default",
        tags="newspaper",
    )
    logger.info("New Business Outreach digest ntfy=%s", notify)
    return notify
