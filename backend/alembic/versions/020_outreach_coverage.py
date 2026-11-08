"""Queue of website lookups and the sub-tile text column.

The website queue is a new empty table, so its index is built inside the
migration transaction. The checkpoint column is nullable with no default.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_outreach_coverage"
down_revision: Union[str, None] = "019_new_business_outreach"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SET LOCAL statement_timeout = 0")
    op.add_column(
        "new_business_outreach_state",
        sa.Column("pending_subtiles", sa.Text(), nullable=True),
    )
    op.create_table(
        "new_business_website_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("venue_category", sa.String(length=120), nullable=True),
        sa.Column("lead_zone", sa.String(length=64), nullable=True),
        sa.Column("lead_tile", sa.String(length=64), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("osm_email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("lead_address", sa.String(length=255), nullable=True),
        sa.Column("osm_brand", sa.String(length=120), nullable=True),
        sa.Column("osm_brand_wikidata", sa.String(length=64), nullable=True),
        sa.Column("osm_operator", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_new_business_website_queue_created",
        "new_business_website_queue",
        ["created_at"],
    )


def downgrade() -> None:
    op.execute("SET LOCAL statement_timeout = 0")
    op.drop_index(
        "ix_new_business_website_queue_created",
        table_name="new_business_website_queue",
    )
    op.drop_table("new_business_website_queue")
    op.drop_column("new_business_outreach_state", "pending_subtiles")
