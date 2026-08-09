"""Records venue/business acceptance of Terms and Conditions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TermsAcceptance(Base):
    """
    Audit record when a venue/business accepts the Platform Terms.

    Stored separately so version history and acceptance source remain queryable.
    """

    __tablename__ = "terms_acceptances"

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
    terms_version: Mapped[str] = mapped_column(String(20), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    acceptance_source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="merchant_registration",
    )
    accepted_by_email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    accepted_by_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    accepted_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<TermsAcceptance merchant={self.merchant_id} "
            f"v={self.terms_version}>"
        )
