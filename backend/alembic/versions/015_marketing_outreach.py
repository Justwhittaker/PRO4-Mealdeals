"""Add merchant outreach tracking to marketing_contacts.

Revision ID: 015_marketing_outreach
Revises: 014_location_area_local
Create Date: 2026-09-19

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_marketing_outreach"
down_revision: Union[str, None] = "014_location_area_local"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_contacts",
        sa.Column("outreach_unsubscribe_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("outreach_unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("last_outreach_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("outreach_excluded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_marketing_contacts_outreach_token",
        "marketing_contacts",
        ["outreach_unsubscribe_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_contacts_outreach_token", table_name="marketing_contacts")
    op.drop_column("marketing_contacts", "outreach_excluded_at")
    op.drop_column("marketing_contacts", "last_outreach_sent_at")
    op.drop_column("marketing_contacts", "outreach_unsubscribed_at")
    op.drop_column("marketing_contacts", "outreach_unsubscribe_token")
