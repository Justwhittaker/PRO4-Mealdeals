"""Partial indexes for the public feed and marketing-contact lookup.

Revision ID: 017_oom_feed_indexes
Revises: 016_newsletter_region
Create Date: 2026-11-06

These indexes already exist on production (created by hand). IF NOT EXISTS
makes this migration a no-op there. Names must match prod exactly.

CONCURRENTLY cannot run inside a transaction. autocommit_block() is required.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "017_oom_feed_indexes"
# Stays on 016_newsletter_region. PR #22 (016_fishy_finger) branches from
# 015_marketing_outreach and must be rebased onto this revision before merge,
# or Alembic will have two heads.
down_revision: Union[str, None] = "016_newsletter_region"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CREATE_INDEXES: tuple[str, ...] = (
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_oom_deals_merchant_active_not_deleted
    ON deals (merchant_id)
    WHERE is_active AND deleted_at IS NULL
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_oom_deals_expires_active
    ON deals (expires_at)
    WHERE is_active
    """,
    """
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_oom_marketing_contacts_lower_business_name
    ON marketing_contacts (lower(business_name))
    """,
)

_INDEX_NAMES: tuple[str, ...] = (
    "ix_oom_deals_merchant_active_not_deleted",
    "ix_oom_deals_expires_active",
    "ix_oom_marketing_contacts_lower_business_name",
)


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # Belt and braces if this file is run without env.py's session SET.
        op.execute("SET statement_timeout = 0")
        for statement in _CREATE_INDEXES:
            op.execute(statement)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        for name in _INDEX_NAMES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
