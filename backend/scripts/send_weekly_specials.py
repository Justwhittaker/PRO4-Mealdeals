#!/usr/bin/env python3
"""Send the Friday Weekly Specials email.

From backend/:

  python scripts/send_weekly_specials.py
  python scripts/send_weekly_specials.py --test-email justin@example.com

``--test-email`` sends only to that subscriber and does not update
``last_emailed_at``. The Friday schedule calls this script with no flag.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.workers.tasks import send_weekly_specials


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send Weekly Specials.")
    parser.add_argument(
        "--test-email",
        default="",
        help=(
            "Send only to this subscriber address. "
            "Does not update last_emailed_at for anyone."
        ),
    )
    args = parser.parse_args(argv)
    test_email = args.test_email.strip() or None
    summary = send_weekly_specials(test_email=test_email)
    print(summary)
    if test_email and summary.get("matched", 1) == 0:
        return 1
    return 0 if summary.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
