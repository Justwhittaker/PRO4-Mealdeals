"""One-zone New Business Outreach dry run.

Prints counts and a few sample rows. Does not write to the database, send
email, post to ntfy, or export a sheet.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.services.new_business_outreach.run import run_zone_dry

logger = logging.getLogger(__name__)

ZoneRunner = Callable[[str], dict[str, Any]]


def _counts_text(summary: dict[str, Any]) -> str:
    lines = [
        "New Business Outreach dry run",
        f"Zone: {summary.get('zone')}",
        "No database writes. No emails. No ntfy. No sheet export.",
        f"Tiles: {summary.get('tiles_run', 0)}",
        f"Found: {summary.get('found', 0)}",
        f"With email: {summary.get('with_email', 0)}",
        f"Excluded already on site: {summary.get('excluded_on_site', 0)}",
        f"Failed tiles: {summary.get('failed', 0)}",
        f"Outreach sends: {summary.get('outreach_sends', 0)}",
        "Samples:",
    ]
    samples = summary.get("samples") or []
    if not samples:
        lines.append("• none")
    for row in samples:
        lines.append(
            "• {name} | {type} | {country} | {address} | {email} | {website} | {source}".format(
                **{key: row.get(key, "") for key in (
                    "name",
                    "type",
                    "country",
                    "address",
                    "email",
                    "website",
                    "source",
                )}
            )
        )
    return "\n".join(lines)


def run_new_business_dry_run(
    zone_id: str,
    *,
    run_zone: ZoneRunner = run_zone_dry,
) -> dict[str, Any]:
    """Run discovery for one zone and print counts plus sample rows."""
    summary = run_zone(zone_id)
    summary["outreach_sends"] = 0
    summary["ntfy"] = None
    text = _counts_text(summary)
    print(text)
    logger.info(
        "New Business Outreach dry run zone=%s found=%s email=%s sends=0",
        zone_id,
        summary.get("found"),
        summary.get("with_email"),
    )
    return {
        "ok": bool(summary.get("ok")),
        "summary": summary,
        "body": text,
        "ntfy": None,
    }


def run_fishy_dry_run(
    zone_id: str,
    *,
    run_zone: ZoneRunner = run_zone_dry,
    build_report: object = None,
) -> dict[str, Any]:
    """Old entry point. Same dry run, still sends nothing."""
    del build_report
    return run_new_business_dry_run(zone_id, run_zone=run_zone)
