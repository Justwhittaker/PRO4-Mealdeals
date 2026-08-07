"""Initial schema with PostGIS locations and meal deal tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-08-06

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "geom",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
    )
    op.create_index("ix_locations_country_code", "locations", ["country_code"])
    op.create_index("ix_locations_city", "locations", ["city"])
    op.create_index(
        "ix_locations_geom",
        "locations",
        ["geom"],
        postgresql_using="gist",
    )

    merchant_category = postgresql.ENUM(
        "supermarket",
        "bistro",
        "hotel",
        "retail",
        name="merchant_category",
        create_type=False,
    )
    tier_level = postgresql.ENUM(
        "free",
        "featured",
        "enterprise",
        name="tier_level",
        create_type=False,
    )
    item_category = postgresql.ENUM(
        "main",
        "side",
        "drink",
        "room",
        "ticket",
        name="item_category",
        create_type=False,
    )

    merchant_category.create(op.get_bind(), checkfirst=True)
    tier_level.create(op.get_bind(), checkfirst=True)
    item_category.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", merchant_category, nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_subscriber", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tier_level", tier_level, nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_merchants_location_id", "merchants", ["location_id"])

    op.create_table(
        "deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("merchant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scraped_raw_url", sa.Text(), nullable=True),
        sa.Column("clean_url", sa.Text(), nullable=True),
        sa.Column("affiliate_url", sa.Text(), nullable=True),
        sa.Column("original_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("deal_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("tier_priority_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_deals_merchant_id", "deals", ["merchant_id"])

    op.create_table(
        "deal_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", item_category, nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.Column("individual_price", sa.Numeric(10, 2), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_deal_items_deal_id", "deal_items", ["deal_id"])

    op.create_table(
        "deal_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language_code", sa.String(length=5), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("deal_id", "language_code", name="uq_deal_translations_deal_language"),
    )
    op.create_index("ix_deal_translations_deal_id", "deal_translations", ["deal_id"])

    op.create_table(
        "currencies",
        sa.Column("code", sa.String(length=3), primary_key=True, nullable=False),
        sa.Column("usd_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("symbol", sa.String(length=5), nullable=False),
    )

    # Seed baseline FX rates
    currencies = sa.table(
        "currencies",
        sa.column("code", sa.String),
        sa.column("usd_rate", sa.Numeric),
        sa.column("symbol", sa.String),
    )
    op.bulk_insert(
        currencies,
        [
            {"code": "USD", "usd_rate": "1.000000", "symbol": "$"},
            {"code": "GBP", "usd_rate": "0.790000", "symbol": "£"},
            {"code": "EUR", "usd_rate": "0.920000", "symbol": "€"},
            {"code": "CAD", "usd_rate": "1.360000", "symbol": "C$"},
            {"code": "AUD", "usd_rate": "1.520000", "symbol": "A$"},
            {"code": "NZD", "usd_rate": "1.650000", "symbol": "NZ$"},
            {"code": "SGD", "usd_rate": "1.340000", "symbol": "S$"},
            {"code": "ZAR", "usd_rate": "18.500000", "symbol": "R"},
            {"code": "PHP", "usd_rate": "56.000000", "symbol": "₱"},
            {"code": "INR", "usd_rate": "83.000000", "symbol": "₹"},
            {"code": "AED", "usd_rate": "3.672500", "symbol": "د.إ"},
        ],
    )


def downgrade() -> None:
    op.drop_table("currencies")
    op.drop_index("ix_deal_translations_deal_id", table_name="deal_translations")
    op.drop_table("deal_translations")
    op.drop_index("ix_deal_items_deal_id", table_name="deal_items")
    op.drop_table("deal_items")
    op.drop_index("ix_deals_merchant_id", table_name="deals")
    op.drop_table("deals")
    op.drop_index("ix_merchants_location_id", table_name="merchants")
    op.drop_table("merchants")
    op.drop_index("ix_locations_geom", table_name="locations")
    op.drop_index("ix_locations_city", table_name="locations")
    op.drop_index("ix_locations_country_code", table_name="locations")
    op.drop_table("locations")

    op.execute("DROP TYPE IF EXISTS item_category")
    op.execute("DROP TYPE IF EXISTS tier_level")
    op.execute("DROP TYPE IF EXISTS merchant_category")
