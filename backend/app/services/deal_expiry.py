"""Deactivate scraped deals past expires_at."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deal import Deal

logger = logging.getLogger(__name__)


def expire_past_due_deals(session: Session) -> int:
    """Set is_active=False on deals whose expires_at is in the past."""
    now = datetime.now(timezone.utc)
    deals = list(
        session.scalars(
            select(Deal).where(
                Deal.is_active.is_(True),
                Deal.expires_at.isnot(None),
                Deal.expires_at <= now,
            )
        ).all()
    )
    for deal in deals:
        deal.is_active = False
    if deals:
        session.commit()
        logger.info("Expired %d past-due deals", len(deals))
    return len(deals)
