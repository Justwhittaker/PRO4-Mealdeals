"""Location model with PostGIS geometry."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Float, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.merchant import Merchant


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        Index("ix_locations_country_code", "country_code"),
        Index("ix_locations_city", "city"),
        Index(
            "ix_locations_geom",
            "geom",
            postgresql_using="gist",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )

    merchants: Mapped[list[Merchant]] = relationship(
        "Merchant",
        back_populates="location",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Location {self.city}, {self.country_code}>"
