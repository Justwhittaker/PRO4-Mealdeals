#!/usr/bin/env python3
"""Dry-run one Fishy Finger zone. Sending stays off.

Writes marketing_contacts lead rows for that zone only. Does not set
last_outreach_sent_at, send email, or post to ntfy. Prints lead counts,
no-specials counts, and the digest text.

Inside the NUC container (after the image that contains this script is running):

    docker exec mealdeals-celery-nuc python /app/scripts/fishy_finger_dry_run.py --zone british_isles
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python /app/scripts/fishy_finger_dry_run.py` and a local backend run.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.fishy_finger.dry_run import run_fishy_dry_run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run one Fishy Finger zone. Inserts lead rows only; "
            "does not send email or post to ntfy."
        )
    )
    parser.add_argument(
        "--zone",
        default="british_isles",
        help="One scrape zone id. Default: british_isles.",
    )
    args = parser.parse_args(argv)
    result = run_fishy_dry_run(args.zone)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
