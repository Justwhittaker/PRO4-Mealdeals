"""Currency exchange-rate model."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    usd_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    symbol: Mapped[str] = mapped_column(String(5), nullable=False, default="$")

    def __repr__(self) -> str:
        return f"<Currency {self.code} rate={self.usd_rate}>"
