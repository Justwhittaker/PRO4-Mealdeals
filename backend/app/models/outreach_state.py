"""Checkpoint row for the weekly New Business Outreach tile cursor."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewBusinessOutreachState(Base):
    """One row. ``next_tile_index`` is the next planet tile to query."""

    __tablename__ = "new_business_outreach_state"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    next_tile_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Sub-tiles still to query, one per line. Empty once the parent tile is done.
    pending_subtiles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
