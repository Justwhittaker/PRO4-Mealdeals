"""How much of marketing_contacts belongs to New Business Outreach.

The 256 MB Postgres plan is shared with deals and merchants. Lead rows live
in ``marketing_contacts`` (the renamed segment, not a second database). The
guard estimates their share of ``pg_total_relation_size`` so other contacts
do not eat the budget, and lead growth still stops at the cap.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.new_business_outreach.constants import (
    LEGACY_SEGMENT_PREFIX,
    NEW_BUSINESS_SEGMENT,
)
from app.services.ntfy import send_ntfy

logger = logging.getLogger(__name__)

# Bytes added between full measurements so a batch cannot overshoot unnoticed.
ESTIMATED_ROW_BYTES = 800
DEFAULT_MAX_MB = 100


def lead_storage_bytes(relation_bytes: int, all_rows: int, lead_rows: int) -> int:
    """Lead share of the relation, including indexes, by row count."""
    if relation_bytes <= 0 or all_rows <= 0 or lead_rows <= 0:
        return 0
    return int(relation_bytes * (lead_rows / all_rows))


def measure_lead_storage(session: Session) -> int:
    """One scan of marketing_contacts plus the relation size."""
    row = session.execute(
        text(
            """
            SELECT
              pg_total_relation_size('marketing_contacts') AS relation_bytes,
              COUNT(*) AS all_rows,
              COUNT(*) FILTER (
                WHERE source_segment = :segment
                   OR lower(COALESCE(source_segment, '')) LIKE :legacy
              ) AS lead_rows
            FROM marketing_contacts
            """
        ),
        {"segment": NEW_BUSINESS_SEGMENT, "legacy": f"{LEGACY_SEGMENT_PREFIX}%"},
    ).one()
    return lead_storage_bytes(
        int(row.relation_bytes or 0),
        int(row.all_rows or 0),
        int(row.lead_rows or 0),
    )


class LeadSizeGuard:
    """Stops inserts once estimated lead storage reaches the cap."""

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max(int(max_bytes), 1)
        self.bytes = 0
        self.stopped = False
        self.warned = False

    def refresh(self, session: Session) -> None:
        self.bytes = measure_lead_storage(session)
        if self.bytes >= self.max_bytes:
            self.stopped = True

    def note_inserts(self, count: int) -> None:
        if count <= 0:
            return
        self.bytes += count * ESTIMATED_ROW_BYTES
        if self.bytes >= self.max_bytes:
            self.stopped = True

    def warn_once(self) -> dict[str, object] | None:
        if not self.stopped or self.warned:
            return None
        self.warned = True
        used_mb = self.bytes / (1024 * 1024)
        cap_mb = self.max_bytes / (1024 * 1024)
        message = (
            "New Business Outreach stopped inserting. "
            f"Lead storage is about {used_mb:.1f} MB and the cap is {cap_mb:.0f} MB."
        )
        logger.warning(message)
        return send_ntfy(
            "New Business Outreach storage",
            message,
            priority="high",
            tags="warning",
        )
