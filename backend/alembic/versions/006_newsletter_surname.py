"""Add surname to newsletter subscribers.

Revision ID: 006_newsletter_surname
Revises: 005_newsletter
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_newsletter_surname"
down_revision: Union[str, None] = "005_newsletter"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "newsletter_subscribers",
        sa.Column(
            "surname",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("newsletter_subscribers", "surname", server_default=None)


def downgrade() -> None:
    op.drop_column("newsletter_subscribers", "surname")
