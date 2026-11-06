"""Fishy Finger Sub lead fields on marketing_contacts.

Revision ID: 018_fishy_finger_sub
Revises: 017_oom_feed_indexes
Create Date: 2026-11-06

Nullable columns only. PostgreSQL 11+ adds a nullable column with no default
without rewriting the table. The source_segment index is a normal CREATE
INDEX in this transaction (not CONCURRENTLY) so SET LOCAL covers it.

Prod's API role has statement_timeout=20s. SET LOCAL disables that for this
transaction only. 017 uses a session-level SET because CREATE INDEX
CONCURRENTLY cannot run inside a transaction.
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
    op.create_index(
        "ix_marketing_contacts_source_segment",
        "marketing_contacts",
        ["source_segment"],
    )


def downgrade() -> None:
    op.execute("SET LOCAL statement_timeout = 0")
    op.drop_index("ix_marketing_contacts_source_segment", table_name="marketing_contacts")
    op.drop_column("marketing_contacts", "specials_checked_at")
    op.drop_column("marketing_contacts", "has_site_specials")
    op.drop_column("marketing_contacts", "email_quality_score")
    op.drop_column("marketing_contacts", "lead_zone")
    op.drop_column("marketing_contacts", "source_segment")
