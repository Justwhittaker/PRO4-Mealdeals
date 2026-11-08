"""New Business Outreach lead columns and checkpoint.

Revision ID: 019_new_business_outreach
Revises: 018_fishy_finger_sub
Create Date: 2026-11-08

Renames source_segment values that start with fishy to new_business_outreach
in batches of 400 so a 256 MB Postgres is not asked to rewrite the table in
one transaction. New columns are nullable and have no default, so PostgreSQL
does not rewrite marketing_contacts to add them.

The partial created_at index is built with CREATE INDEX CONCURRENTLY, same
as 018. SET LOCAL statement_timeout covers the column adds. SET
statement_timeout covers the autocommit batches and the index build.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_new_business_outreach"
down_revision: Union[str, None] = "018_fishy_finger_sub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BATCH = sa.text(
    """
    WITH batch AS (
        SELECT id
        FROM marketing_contacts
        WHERE source_segment IS NOT NULL
          AND lower(source_segment) LIKE :pattern
          AND lower(source_segment) <> :target
        LIMIT 400
    )
    UPDATE marketing_contacts AS mc
    SET source_segment = :target
    FROM batch
    WHERE mc.id = batch.id
    """
)


def _rename_segments(pattern: str, target: str) -> None:
    connection = op.get_bind()
    while True:
        result = connection.execute(_BATCH, {"pattern": pattern, "target": target})
        if not result.rowcount:
            return


def upgrade() -> None:
    op.execute("SET LOCAL statement_timeout = 0")
    op.add_column(
        "marketing_contacts",
        sa.Column("lead_address", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("lead_tile", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "marketing_contacts",
        sa.Column("lead_source", sa.String(length=32), nullable=True),
    )
    op.create_table(
        "new_business_outreach_state",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("next_tile_index", sa.Integer(), nullable=False),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "INSERT INTO new_business_outreach_state (id, next_tile_index, cycle) "
        "VALUES (1, 0, 1)"
    )
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        _rename_segments("fishy%", "new_business_outreach")
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_marketing_contacts_nbo_created
            ON marketing_contacts (created_at)
            WHERE source_segment = 'new_business_outreach'
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("SET statement_timeout = 0")
        op.execute(
            "DROP INDEX CONCURRENTLY IF EXISTS ix_marketing_contacts_nbo_created"
        )
        _rename_segments("new_business_outreach", "fishy_finger_sub")
    op.execute("SET LOCAL statement_timeout = 0")
    op.drop_table("new_business_outreach_state")
    op.drop_column("marketing_contacts", "lead_source")
    op.drop_column("marketing_contacts", "lead_tile")
    op.drop_column("marketing_contacts", "lead_address")
