"""Bust the public deal page after an edit, deactivation, or delete."""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal
from app.models.location import Location
from app.models.merchant import Merchant
from app.services.frontend_revalidate import revalidate_after_scrape


async def queue_public_deal_revalidate(
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    deal_id: UUID,
) -> None:
    """Revalidate this deal's tag and its city tag after the response commits.

    FastAPI runs dependency teardown (the session commit) before background
    tasks, so the follow-up fetch sees the new row. The global `deals` tag
    is not included: one merchant edit must not drop every city.
    """
    row = (
        await session.execute(
            select(Location.country_code, Location.city)
            .join(Merchant, Merchant.location_id == Location.id)
            .join(Deal, Deal.merchant_id == Merchant.id)
            .where(Deal.id == deal_id)
        )
    ).one_or_none()
    areas: set[tuple[str, str]] = set()
    if row is not None and row.country_code and row.city:
        areas.add((row.country_code, row.city))
    background_tasks.add_task(
        revalidate_after_scrape,
        areas=areas,
        extra_tags=[f"deal-{deal_id}"],
    )
