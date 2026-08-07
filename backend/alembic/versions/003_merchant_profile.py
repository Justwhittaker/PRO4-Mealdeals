"""Merchant profile fields + deal repost lineage.

Revision ID: 003_profile
Revises: 002_slots
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_profile"
down_revision: Union[str, None] = "002_slots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("merchants", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column(
        "merchants", sa.Column("contact_name", sa.String(length=255), nullable=True)
    )
    op.add_column("merchants", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column(
        "merchants", sa.Column("website", sa.String(length=500), nullable=True)
    )
    op.add_column("merchants", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column(
        "merchants", sa.Column("logo_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "merchants",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "merchants",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column(
        "merchants",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_merchants_email", "merchants", ["email"], unique=True)
    op.create_index(
        "ix_merchants_stripe_customer_id",
        "merchants",
        ["stripe_customer_id"],
        unique=False,
    )

    op.add_column(
        "deals",
        sa.Column("reposted_from_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_deals_reposted_from_id", "deals", ["reposted_from_id"])
    op.create_foreign_key(
        "fk_deals_reposted_from_id",
        "deals",
        "deals",
        ["reposted_from_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_deals_reposted_from_id", "deals", type_="foreignkey")
    op.drop_index("ix_deals_reposted_from_id", table_name="deals")
    op.drop_column("deals", "reposted_from_id")

    op.drop_index("ix_merchants_stripe_customer_id", table_name="merchants")
    op.drop_index("ix_merchants_email", table_name="merchants")
    op.drop_column("merchants", "updated_at")
    op.drop_column("merchants", "created_at")
    op.drop_column("merchants", "stripe_customer_id")
    op.drop_column("merchants", "logo_url")
    op.drop_column("merchants", "bio")
    op.drop_column("merchants", "website")
    op.drop_column("merchants", "phone")
    op.drop_column("merchants", "contact_name")
    op.drop_column("merchants", "email")
