"""Add deals.deleted_at for soft-delete (keep analytics rows).

Revision ID: 011_deal_deleted_at
Revises: 010_deal_venue_category
Create Date: 2026-08-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_deal_deleted_at"
down_revision: Union[str, None] = "010_deal_venue_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deals_deleted_at", "deals", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_deals_deleted_at", table_name="deals")
    op.drop_column("deals", "deleted_at")
