"""Deal translation model with composite uniqueness."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal import Deal


class DealTranslation(Base):
    __tablename__ = "deal_translations"
    __table_args__ = (
        UniqueConstraint(
            "deal_id",
            "language_code",
            name="uq_deal_translations_deal_language",
        ),
    )

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
    language_code: Mapped[str] = mapped_column(String(5), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    deal: Mapped[Deal] = relationship("Deal", back_populates="translations")

    def __repr__(self) -> str:
        return f"<DealTranslation {self.language_code}: {self.title}>"
