"""Deal design requests + slot-exempt deals.

Revision ID: 004_design
Revises: 003_profile
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_design"
down_revision: Union[str, None] = "003_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column(
            "slot_exempt",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "deals", sa.Column("image_url", sa.String(length=500), nullable=True)
    )

    status = postgresql.ENUM(
        "draft",
        "pending_payment",
        "paid",
        "in_design",
        "posted",
        "cancelled",
        name="design_request_status",
        create_type=False,
    )
    status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "design_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("photo_urls", postgresql.ARRAY(sa.String(length=500)), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fulfillment_image_url", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_design_requests_merchant_id", "design_requests", ["merchant_id"])
    op.create_index(
        "ix_design_requests_stripe_checkout_session_id",
        "design_requests",
        ["stripe_checkout_session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_design_requests_stripe_checkout_session_id", table_name="design_requests"
    )
    op.drop_index("ix_design_requests_merchant_id", table_name="design_requests")
    op.drop_table("design_requests")
    op.execute("DROP TYPE IF EXISTS design_request_status")
    op.drop_column("deals", "image_url")
    op.drop_column("deals", "slot_exempt")
