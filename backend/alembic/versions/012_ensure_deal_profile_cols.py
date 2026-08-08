"""Ensure deals.venue_category + deals.deleted_at exist (idempotent).

Revision ID: 012_ensure_deal_profile_cols
Revises: 011_deal_deleted_at
Create Date: 2026-08-08

Safe to run if 010/011 already applied — uses IF NOT EXISTS so a partial
prod DB (or skipped upgrade) still gets the soft-delete / category columns.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_ensure_deal_profile_cols"
down_revision: Union[str, None] = "011_deal_deleted_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE deals
        ADD COLUMN IF NOT EXISTS venue_category VARCHAR(120)
        """
    )
    op.execute(
        """
        ALTER TABLE deals
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_deals_deleted_at
        ON deals (deleted_at)
        """
    )


def downgrade() -> None:
    # Do not drop columns here — 010/011 own the canonical downgrade path.
    pass
