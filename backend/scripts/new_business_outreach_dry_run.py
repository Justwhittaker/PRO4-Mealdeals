#!/usr/bin/env python3
"""Dry-run one New Business Outreach zone. Nothing is stored or sent.

Example:
    docker exec mealdeals-celery-nuc python /app/scripts/new_business_outreach_dry_run.py --zone british_isles
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.new_business_outreach.dry_run import run_new_business_dry_run  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run one New Business Outreach zone. "
            "Does not write to the database, send email, or post to ntfy."
        )
    )
    parser.add_argument(
        "--zone",
        required=True,
        help="Coarse zone id, for example british_isles, or a tile id such as ie-0.",
    )
    args = parser.parse_args()
    result = run_new_business_dry_run(args.zone)
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
