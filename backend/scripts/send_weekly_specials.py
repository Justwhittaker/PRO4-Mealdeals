#!/usr/bin/env python3
"""Send the Friday Weekly Specials email.

From backend/:

  python scripts/send_weekly_specials.py
  python scripts/send_weekly_specials.py --test-email justin@example.com

``--test-email`` sends only to that subscriber and does not update
``last_emailed_at``. The Friday schedule calls this script with no flag.

Exit status:

* 0 when at least one delivery succeeded. Other recipients may have failed;
  that is logged as a warning and does not fail the workflow.
* 0 when there was nothing to attempt (no subscribers, or every row was
  skipped). A log line records that.
* 1 when ``--test-email`` does not match a subscriber, or every attempted
  delivery failed.

A database, configuration, or provider authentication error is raised and
the process exits nonzero. Those are not counted as one bad recipient.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.workers.tasks import send_weekly_specials

logger = logging.getLogger(__name__)


def exit_code_for_summary(
    summary: dict[str, int],
    *,
    test_email: str | None,
) -> int:
    """Map a send summary to a process exit code. Does not send mail."""
    if test_email and summary.get("matched", 1) == 0:
        logger.error("Weekly specials test recipient was not found: %s", test_email)
        return 1
    sent = int(summary.get("sent", 0) or 0)
    failed = int(summary.get("failed", 0) or 0)
    skipped = int(summary.get("skipped", 0) or 0)
    if sent == 0 and failed == 0:
        logger.info(
            "Weekly specials finished with no deliveries "
            "(sent=0 failed=0 skipped=%s)",
            skipped,
        )
        return 0
    if sent == 0 and failed > 0:
        logger.error(
            "Weekly specials: every attempted delivery failed "
            "(failed=%s skipped=%s)",
            failed,
            skipped,
        )
        return 1
    if failed > 0:
        logger.warning(
            "Weekly specials partial failure: sent=%s failed=%s skipped=%s",
            sent,
            failed,
            skipped,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
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
    return exit_code_for_summary(summary, test_email=test_email)


if __name__ == "__main__":
    raise SystemExit(main())
