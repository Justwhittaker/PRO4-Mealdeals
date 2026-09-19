#!/usr/bin/env python3
"""Pick the current continental scrape zone (UTC) and run ingest + revalidate."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow `python backend/scripts/pick_and_scrape_zone.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scrapers.zones import ZONE_BEAT_SLOTS, ZONE_ORDER  # noqa: E402
from app.services.scrape_runner import scrape_and_ingest_zone  # noqa: E402


def zone_for_now() -> str | None:
    """Return zone id when current UTC matches a Celery Beat slot, else None."""
    now = datetime.now(timezone.utc)
    hour_in_cycle = now.hour % 6
    for zone_id in ZONE_ORDER:
        minute, hour_offset = ZONE_BEAT_SLOTS[zone_id]
        if now.minute == minute and hour_in_cycle == hour_offset:
            return zone_id
    return None


def main() -> int:
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
