"""Deactivate scraped deals past expires_at."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.location import Location
from app.models.merchant import Merchant

logger = logging.getLogger(__name__)


def is_publicly_listed(
    *,
    is_active: bool,
    deleted_at: datetime | None,
    expires_at: datetime | None,
    now: datetime,
) -> bool:
    """True when the public deal page should render this row."""
    if deleted_at is not None or not is_active:
        return False
    if expires_at is not None and expires_at <= now:
        return False
    return True


@dataclass(frozen=True)
class ExpiredDeal:
    id: UUID
    country_code: str | None
    city: str | None


def expire_past_due_deals(session: Session) -> list[ExpiredDeal]:
    """Set is_active=False on deals whose expires_at is in the past.

    Returns the deals that changed, with country and city when the merchant
    has a location, so the caller can bust those city and deal caches.
    """
    now = datetime.now(timezone.utc)
    rows = session.execute(
        select(Deal.id, Location.country_code, Location.city)
        .join(Merchant, Deal.merchant_id == Merchant.id)
        .outerjoin(Location, Merchant.location_id == Location.id)
        .where(
            Deal.is_active.is_(True),
            Deal.expires_at.isnot(None),
            Deal.expires_at <= now,
        )
    ).all()
    expired = [
        ExpiredDeal(id=deal_id, country_code=country_code, city=city)
        for deal_id, country_code, city in rows
    ]
    if not expired:
        return []
    session.execute(
        update(Deal)
        .where(Deal.id.in_([row.id for row in expired]))
        .values(is_active=False)
    )
    session.commit()
    logger.info("Expired %d past-due deals", len(expired))
    return expired


def revalidate_kwargs_for_expired(
    expired: list[ExpiredDeal],
) -> dict[str, object]:
    """City tags plus deal-{id} tags. Global home bust is included once."""
    areas: set[tuple[str, str]] = set()
    extra_tags: list[str] = []
    for row in expired:
        extra_tags.append(f"deal-{row.id}")
        if row.country_code and row.city:
            areas.add((row.country_code, row.city))
    return {
        "areas": areas,
        "include_global": True,
        "extra_tags": extra_tags,
    }
