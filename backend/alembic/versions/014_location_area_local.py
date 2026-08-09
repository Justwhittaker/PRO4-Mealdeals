"""Location area_local for nested hub-town labels."""

from alembic import op
import sqlalchemy as sa

revision = "014_location_area_local"
down_revision = "013_terms_acceptances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column("area_local", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_locations_area_local",
        "locations",
        ["area_local"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_locations_area_local", table_name="locations")
    op.drop_column("locations", "area_local")
