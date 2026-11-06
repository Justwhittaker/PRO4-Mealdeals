"""Fishy Finger Sub lead fields on marketing_contacts.

Revision ID: 018_fishy_finger_sub
Revises: 017_oom_feed_indexes
Create Date: 2026-11-06

Nullable columns only. PostgreSQL 11+ adds a nullable column with no default
without rewriting the table. Those adds stay in this migration's transaction.

The source_segment index uses CREATE INDEX CONCURRENTLY, same as
017_oom_feed_indexes. CONCURRENTLY cannot run inside a transaction, so it
sits in autocommit_block(). That commits the column adds first, then builds
the index without locking writes. SET statement_timeout = 0 inside the block
covers the API role's 20 second timeout. SET LOCAL still covers the column
adds, and ends when that transaction commits.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_fishy_finger_sub"
down_revision: Union[str, None] = "017_oom_feed_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("SET LOCAL statement_timeout = 0")
    op.add_column(
        "marketing_contacts",
        sa.Column("source_segment", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("lead_zone", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("email_quality_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("has_site_specials", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("specials_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    with op.get_context().autocommit_block():
        # Belt and braces if this file is run without env.py's session SET.
        # CREATE INDEX CONCURRENTLY cannot run inside a transaction.
        op.execute("SET statement_timeout = 0")
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_marketing_contacts_source_segment
            ON marketing_contacts (source_segment)
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_marketing_contacts_source_segment"
        )
    op.execute("SET LOCAL statement_timeout = 0")
    op.drop_column("marketing_contacts", "specials_checked_at")
    op.drop_column("marketing_contacts", "has_site_specials")
    op.drop_column("marketing_contacts", "email_quality_score")
    op.drop_column("marketing_contacts", "lead_zone")
    op.drop_column("marketing_contacts", "source_segment")
