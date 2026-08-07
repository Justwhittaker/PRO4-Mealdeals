"""Marketing contacts table for scraped business outreach export.

Revision ID: 008_marketing
Revises: 007_trial
Create Date: 2026-08-07

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_marketing"
down_revision: Union[str, None] = "007_trial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("about_blurb", sa.Text(), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("venue_category", sa.String(length=120), nullable=True),
        sa.Column(
            "last_scraped_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
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
        sa.UniqueConstraint(
            "website",
            "country_code",
            "city",
            name="uq_marketing_contacts_website_geo",
        ),
    )
    op.create_index(
        "ix_marketing_contacts_email",
        "marketing_contacts",
        ["email"],
    )
    op.create_index(
        "ix_marketing_contacts_country_code",
        "marketing_contacts",
        ["country_code"],
    )
    op.create_index(
        "ix_marketing_contacts_business_name",
        "marketing_contacts",
        ["business_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_contacts_business_name", table_name="marketing_contacts")
    op.drop_index("ix_marketing_contacts_country_code", table_name="marketing_contacts")
    op.drop_index("ix_marketing_contacts_email", table_name="marketing_contacts")
    op.drop_table("marketing_contacts")
