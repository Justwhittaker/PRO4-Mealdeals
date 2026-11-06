"""One-zone Fishy Finger run with sending left off.

Inserts marketing_contacts lead rows for the zone. Does not set
``last_outreach_sent_at``, send email, or post the Sunday ntfy digest.
The digest text is printed instead.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.core.task_errors import reraise_if_fatal
from app.scrapers.zones import SCRAPE_ZONES
from app.services.fishy_finger.digest import (
    build_fishy_digest_report,
    format_fishy_digest,
)
from app.services.fishy_finger.leads import run_fishy_finger_zone

logger = logging.getLogger(__name__)

ZoneRunner = Callable[..., dict[str, Any]]
ReportBuilder = Callable[[], dict[str, Any]]


def _counts_text(zone: str, summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Fishy Finger dry run",
            f"Zone: {zone}",
            "Sending is disabled. This writes marketing_contacts lead rows only.",
            "It does not set last_outreach_sent_at, send email, or post to ntfy.",
            f"Candidates: {summary.get('candidates', 0)}",
            f"Leads inserted: {summary.get('leads_inserted', 0)}",
            f"No specials: {summary.get('no_specials', 0)}",
            f"Has specials: {summary.get('has_specials', 0)}",
            f"Specials unknown: {summary.get('specials_unknown', 0)}",
            f"Skipped known: {summary.get('skipped_known', 0)}",
            f"Outreach sends: {summary.get('outreach_sends', 0)}",
        ]
    )


def run_fishy_dry_run(
    zone_id: str,
    *,
    run_zone: ZoneRunner = run_fishy_finger_zone,
    build_report: ReportBuilder = build_fishy_digest_report,
) -> dict[str, Any]:
    """Scrape one zone, print counts and the digest, and do not notify."""
    zone = zone_id.strip().lower()
    if zone not in SCRAPE_ZONES:
        message = f"Unknown fishy zone {zone_id!r}"
        print(message)
        return {
            "ok": False,
            "summary": {
                "zone": zone,
                "ok": False,
                "status": "skipped",
                "outreach_sends": 0,
            },
            "body": message,
            "ntfy": None,
        }

    summary = run_zone(zone, dry_run=True)
    summary["outreach_sends"] = 0
    summary["ntfy"] = None
    print(_counts_text(zone, summary))

    digest_ok = True
    try:
        report = build_report()
        body = format_fishy_digest(report)
    except Exception as exc:  # noqa: BLE001 — counts were already printed
        reraise_if_fatal(exc)
        logger.exception("Fishy dry run digest failed for %s", zone)
        body = f"Digest could not be built: {exc}"
        digest_ok = False

    print("Digest text (not posted):")
    print(body)
    logger.info(
        "Fishy Finger dry run zone=%s inserted=%s no_specials=%s sends=0",
        zone,
        summary.get("leads_inserted"),
        summary.get("no_specials"),
    )
    return {
        "ok": bool(summary.get("ok")) and digest_ok,
        "summary": summary,
        "body": body,
        "ntfy": None,
    }
