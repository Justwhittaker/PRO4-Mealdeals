"""Merchant profile model (subscription + venue identity)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.location import Location

# Priority: free first month (card on file) → €20/mo (geo currency) · 3 slots
PAID_DEAL_SLOT_LIMIT = 3


class MerchantCategory(str, enum.Enum):
    SUPERMARKET = "supermarket"
    BISTRO = "bistro"
    HOTEL = "hotel"
    RETAIL = "retail"


class TierLevel(str, enum.Enum):
    FREE = "free"
    FEATURED = "featured"
    ENTERPRISE = "enterprise"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Merchant(Base):
    """
    Merchant profile — venue identity + subscription state + deal history owner.

    Deals stay linked forever (active or inactive) so merchants can rebuild
    history and repost past offers into an open priority slot.
    """

    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[MerchantCategory] = mapped_column(
        Enum(
            MerchantCategory,
            name="merchant_category",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=MerchantCategory.RETAIL,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Profile / login identity
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Subscription / Priority slots
    is_subscriber: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tier_level: Mapped[TierLevel] = mapped_column(
        Enum(
            TierLevel,
            name="tier_level",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=TierLevel.FREE,
    )
    deal_slot_limit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscription_phase: Mapped[str] = mapped_column(
        String(20), default="none", nullable=False
    )
    # True once the free Priority month has been claimed (anti-abuse)
    used_free_trial: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    location: Mapped[Location] = relationship(
        "Location",
        back_populates="merchants",
        lazy="joined",
    )
    deals: Mapped[list[Deal]] = relationship(
        "Deal",
        back_populates="merchant",
        lazy="selectin",
        cascade="all, delete-orphan",
        foreign_keys="Deal.merchant_id",
    )

    def __repr__(self) -> str:
        return f"<Merchant {self.name} ({self.tier_level.value})>"
