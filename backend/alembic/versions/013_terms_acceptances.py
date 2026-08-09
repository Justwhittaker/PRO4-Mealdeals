"""Add terms_acceptances table for venue Terms agreement records.

Revision ID: 013_terms_acceptances
Revises: 012_ensure_deal_profile_cols
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_terms_acceptances"
down_revision: Union[str, None] = "012_ensure_deal_profile_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "terms_acceptances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("terms_version", sa.String(length=20), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "acceptance_source",
            sa.String(length=64),
            nullable=False,
            server_default="merchant_registration",
        ),
        sa.Column("accepted_by_email", sa.String(length=255), nullable=True),
        sa.Column("accepted_by_name", sa.String(length=255), nullable=True),
        sa.Column("accepted_by_user_id", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_terms_acceptances_merchant_id",
        "terms_acceptances",
        ["merchant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_terms_acceptances_merchant_id", table_name="terms_acceptances")
    op.drop_table("terms_acceptances")
