"""Paid deal-design requests (€20 one-time, slot-exempt, 2-month run)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.merchant import Merchant


class DesignRequestStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    IN_DESIGN = "in_design"
    POSTED = "posted"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DesignRequest(Base):
    """
    Merchant submits copy + optional photos, pays €20, then ops emails/uploads
    the finished creative — which auto-posts as a slot-exempt deal for 2 months.
    """

    __tablename__ = "design_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    details: Mapped[str] = mapped_column(Text, nullable=False, default="")
    photo_urls: Mapped[list[str]] = mapped_column(
        ARRAY(String(500)), nullable=False, default=list
    )
    status: Mapped[DesignRequestStatus] = mapped_column(
        Enum(
            DesignRequestStatus,
            name="design_request_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DesignRequestStatus.PENDING_PAYMENT,
    )
    stripe_checkout_session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
    )
    fulfillment_image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    merchant: Mapped[Merchant] = relationship("Merchant", lazy="joined")
    deal: Mapped[Optional[Deal]] = relationship(
        "Deal", foreign_keys=[deal_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DesignRequest {self.id} {self.status.value}>"
