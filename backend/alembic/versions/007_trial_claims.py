"""Free-trial abuse claims (email / business / location).

Revision ID: 007_trial
Revises: 006_newsletter_surname
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_trial"
down_revision: Union[str, None] = "006_newsletter_surname"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column(
            "used_free_trial",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "trial_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email_normalized", sa.String(length=255), nullable=False),
        sa.Column(
            "business_name_normalized", sa.String(length=255), nullable=False
        ),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "email_normalized", name="uq_trial_claims_email_normalized"
        ),
    )
    op.create_index(
        "ix_trial_claims_merchant_id", "trial_claims", ["merchant_id"]
    )
    op.create_index(
        "ix_trial_claims_business_name_normalized",
        "trial_claims",
        ["business_name_normalized"],
    )
    op.create_index(
        "ix_trial_claims_location_id", "trial_claims", ["location_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_trial_claims_location_id", table_name="trial_claims")
    op.drop_index(
        "ix_trial_claims_business_name_normalized", table_name="trial_claims"
    )
    op.drop_index("ix_trial_claims_merchant_id", table_name="trial_claims")
    op.drop_table("trial_claims")
    op.drop_column("merchants", "used_free_trial")
