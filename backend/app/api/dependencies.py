"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Optional

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import verify_optional_api_key
from app.services.currency import CurrencyService

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Provide a shared async Redis client."""
    global _redis_client
    settings = get_settings()
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    yield _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def get_currency_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[aioredis.Redis, Depends(get_redis)],
) -> CurrencyService:
    return CurrencyService(session=session, redis_client=redis_client)


DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]
AppSettings = Annotated[Settings, Depends(get_settings)]
OptionalApiKey = Annotated[Optional[str], Depends(verify_optional_api_key)]
CurrencySvc = Annotated[CurrencyService, Depends(get_currency_service)]
