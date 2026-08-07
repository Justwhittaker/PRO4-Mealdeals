"""Affiliate redirect endpoint: GET /go/{deal_id}."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.api.dependencies import DbSession, RedisClient
from app.core.config import get_settings
from app.models.deal import Deal

router = APIRouter(tags=["redirect"])


async def _ensure_click_table(db: DbSession) -> None:
    """Create click_events table if missing (lightweight audit log)."""
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS click_events (
                id BIGSERIAL PRIMARY KEY,
                deal_id UUID NOT NULL,
                affiliate_url TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


@router.get("/go/{deal_id}", response_class=RedirectResponse)
async def go_redirect(
    deal_id: UUID,
    request: Request,
    db: DbSession,
    redis: RedisClient,
) -> RedirectResponse:
    """
    Lookup deal affiliate_url, async-log the click to Redis + Postgres, HTTP 302.
    """
    deal = await db.get(Deal, deal_id)
    if deal is None or not deal.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found")

    target = deal.affiliate_url or deal.clean_url or deal.scraped_raw_url
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal has no redirect URL",
        )

    settings = get_settings()
    now = datetime.now(timezone.utc).isoformat()
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")

    # Redis click log (fast path for analytics / rate dashboards)
    click_payload = {
        "deal_id": str(deal_id),
        "affiliate_url": target,
        "ip": client_ip,
        "user_agent": user_agent,
        "ts": now,
    }
    redis_key = f"clicks:{deal_id}"
    await redis.lpush(redis_key, json.dumps(click_payload))
    await redis.ltrim(redis_key, 0, 999)
    await redis.expire(redis_key, settings.click_log_ttl)
    await redis.incr(f"clicks:count:{deal_id}")

    # Durable Postgres log
    await _ensure_click_table(db)
    await db.execute(
        text(
            """
            INSERT INTO click_events (deal_id, affiliate_url, ip_address, user_agent, created_at)
            VALUES (:deal_id, :affiliate_url, :ip_address, :user_agent, NOW())
            """
        ),
        {
            "deal_id": str(deal_id),
            "affiliate_url": target,
            "ip_address": client_ip,
            "user_agent": user_agent[:512] if user_agent else None,
        },
    )

    return RedirectResponse(url=target, status_code=status.HTTP_302_FOUND)
