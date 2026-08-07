"""Widen deals.image_url to Text for uploaded deal photos.

Revision ID: 009_deal_image
Revises: 008_marketing
Create Date: 2026-08-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_deal_image"
down_revision: Union[str, None] = "008_marketing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "deals",
        "image_url",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "deals",
        "image_url",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
