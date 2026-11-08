"""Places discovered on OSM that still need a website email lookup.

Rows are short strings only. They are deleted once the lookup finishes or
the next weekly run spends its fetch budget on them.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NewBusinessWebsiteQueue(Base):
    __tablename__ = "new_business_website_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    venue_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lead_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_tile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    osm_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    osm_brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    osm_brand_wikidata: Mapped[str | None] = mapped_column(String(64), nullable=True)
    osm_operator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
