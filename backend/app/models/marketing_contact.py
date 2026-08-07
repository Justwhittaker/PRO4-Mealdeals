"""Scraped hospitality business contacts for marketing export (separate from deals)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MarketingContact(Base):
    """
    Business contact ledger for outbound marketing.

    Kept separate from `merchants` / `deals` so export lists stay clean.
    Soft-updates on re-scrape (matched by website+country or email).
    """

    __tablename__ = "marketing_contacts"
    __table_args__ = (
        UniqueConstraint(
            "website",
            "country_code",
            "city",
            name="uq_marketing_contacts_website_geo",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    about_blurb: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    venue_category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    last_scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
