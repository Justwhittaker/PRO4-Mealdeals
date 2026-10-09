"""Store subscriber state or region for Weekly Specials.

Revision ID: 016_newsletter_region
Revises: 015_marketing_outreach
Create Date: 2026-10-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_newsletter_region"
down_revision: Union[str, None] = "015_marketing_outreach"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "newsletter_subscribers",
        sa.Column("region", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("newsletter_subscribers", "region")
