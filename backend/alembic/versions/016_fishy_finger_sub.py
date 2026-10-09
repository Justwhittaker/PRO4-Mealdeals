"""Fishy Finger Sub lead fields on marketing_contacts.

Revision ID: 016_fishy_finger
Revises: 015_marketing_outreach
Create Date: 2026-10-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_fishy_finger"
down_revision: Union[str, None] = "015_marketing_outreach"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_contacts",
        sa.Column("source_segment", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("lead_zone", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("email_quality_score", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_marketing_contacts_source_segment",
        "marketing_contacts",
        ["source_segment"],
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_contacts_source_segment", table_name="marketing_contacts")
    op.drop_column("marketing_contacts", "email_quality_score")
    op.drop_column("marketing_contacts", "lead_zone")
    op.drop_column("marketing_contacts", "source_segment")
