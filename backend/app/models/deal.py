"""Deal and DealItem models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.merchant import Merchant
    from app.models.translation import DealTranslation


class ItemCategory(str, enum.Enum):
    MAIN = "main"
    SIDE = "side"
    DRINK = "drink"
    ROOM = "room"
    TICKET = "ticket"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # When set, this deal was reposted from an earlier profile deal
    reposted_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Designed specials (€20 design) do not consume Priority subscription slots
    slot_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Parent hospitality category id (e.g. restaurants-cafes-bistros) or legacy label.
    venue_category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    scraped_raw_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clean_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affiliate_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deal_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tier_priority_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    merchant: Mapped[Merchant] = relationship(
        "Merchant",
        back_populates="deals",
        lazy="joined",
    )
    items: Mapped[list[DealItem]] = relationship(
        "DealItem",
        back_populates="deal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    translations: Mapped[list[DealTranslation]] = relationship(
        "DealTranslation",
        back_populates="deal",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Deal {self.id} {self.deal_price} {self.currency_code}>"


class DealItem(Base):
    __tablename__ = "deal_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[ItemCategory] = mapped_column(
        Enum(ItemCategory, name="item_category", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ItemCategory.MAIN,
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    individual_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    deal: Mapped[Deal] = relationship("Deal", back_populates="items")

    def __repr__(self) -> str:
        return f"<DealItem {self.item_name} ({self.category.value})>"
