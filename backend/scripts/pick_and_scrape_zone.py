#!/usr/bin/env python3
"""Pick the current continental scrape zone (UTC) and run ingest + revalidate."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python backend/scripts/pick_and_scrape_zone.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scrapers.zones import (  # noqa: E402
    ZONE_BEAT_SLOTS,
    ZONE_CYCLE_BASE_HOURS,
    ZONE_ORDER,
)
from app.services.scrape_runner import scrape_and_ingest_zone  # noqa: E402


def zone_for_now() -> str | None:
    """Return zone id when current UTC matches a Celery Beat slot, else None."""
    now = datetime.now(timezone.utc)
    for base_hour in ZONE_CYCLE_BASE_HOURS:
        for zone_id in ZONE_ORDER:
            minute, hour_offset = ZONE_BEAT_SLOTS[zone_id]
            if now.hour == base_hour + hour_offset and now.minute == minute:
                return zone_id
    return None


def main() -> int:
    forced = (os.environ.get("SCRAPE_ZONE_ID") or "").strip().lower()
    if forced:
        if forced not in ZONE_BEAT_SLOTS:
            print(f"Unknown SCRAPE_ZONE_ID: {forced}")
            print("Valid zones:", ", ".join(ZONE_ORDER))
            return 1
        zone = forced
        print(f"Using forced zone: {zone}")
    else:
        zone = zone_for_now()
        if zone is None:
            print("No scrape zone scheduled for this UTC slot — skipping.")
            return 0

    print(f"Running scheduled zone scrape: {zone}")
    result = scrape_and_ingest_zone(zone)
    print(
        "Done:",
        f"areas={result.get('areas')}",
        f"discovered={result.get('discovered')}",
        f"ingested={result.get('ingested')}",
        f"revalidate={result.get('frontend_revalidate')}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
