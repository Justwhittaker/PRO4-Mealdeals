"""Add merchant deal slots and subscription phase.

Revision ID: 002_slots
Revises: 001_initial
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_slots"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column(
            "deal_slot_limit",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "merchants",
        sa.Column(
            "subscription_phase",
            sa.String(length=20),
            nullable=False,
            server_default="none",
        ),
    )
    # Paying merchants already marked featured/enterprise get 3 slots
    op.execute(
        """
        UPDATE merchants
        SET deal_slot_limit = 3,
            subscription_phase = 'monthly',
            is_subscriber = true
        WHERE tier_level IN ('featured', 'enterprise')
        """
    )


def downgrade() -> None:
    op.drop_column("merchants", "subscription_phase")
    op.drop_column("merchants", "deal_slot_limit")
