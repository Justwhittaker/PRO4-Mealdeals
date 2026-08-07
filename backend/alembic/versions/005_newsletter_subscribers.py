"""Newsletter subscribers with soft unsubscribe.

Revision ID: 005_newsletter
Revises: 004_design
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_newsletter"
down_revision: Union[str, None] = "004_design"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "newsletter_subscribers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column(
            "is_subscribed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribe_token", sa.String(length=64), nullable=False),
        sa.Column("last_emailed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_newsletter_subscribers_email"),
        sa.UniqueConstraint(
            "unsubscribe_token", name="uq_newsletter_subscribers_token"
        ),
    )
    op.create_index(
        "ix_newsletter_subscribers_email",
        "newsletter_subscribers",
        ["email"],
        unique=True,
    )
    op.create_index(
        "ix_newsletter_subscribers_is_subscribed",
        "newsletter_subscribers",
        ["is_subscribed"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_newsletter_subscribers_is_subscribed",
        table_name="newsletter_subscribers",
    )
    op.drop_index(
        "ix_newsletter_subscribers_email", table_name="newsletter_subscribers"
    )
    op.drop_table("newsletter_subscribers")
