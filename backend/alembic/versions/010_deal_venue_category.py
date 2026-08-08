"""Add deals.venue_category for merchant + scrape browse filters.

Revision ID: 010_deal_venue_category
Revises: 009_deal_image
Create Date: 2026-08-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_deal_venue_category"
down_revision: Union[str, None] = "009_deal_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column("venue_category", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("deals", "venue_category")
