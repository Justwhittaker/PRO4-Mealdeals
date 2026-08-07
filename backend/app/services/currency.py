"""Currency conversion with DB rates and Redis cache."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.currency import Currency

_TWO_PLACES = Decimal("0.01")


class CurrencyService:
    """Resolve FX rates from Redis first, then PostgreSQL."""

    def __init__(
        self,
        session: AsyncSession,
        redis_client: aioredis.Redis | None = None,
    ) -> None:
        self.session = session
        self.redis = redis_client
        self.settings = get_settings()

    def _cache_key(self, code: str) -> str:
        return f"fx:usd_rate:{code.upper()}"

    async def get_usd_rate(self, code: str) -> Decimal | None:
        code = code.upper()
        if code == "USD":
            return Decimal("1.000000")

        if self.redis is not None:
            cached = await self.redis.get(self._cache_key(code))
            if cached is not None:
                return Decimal(cached if isinstance(cached, str) else cached.decode())

        result = await self.session.execute(
            select(Currency).where(Currency.code == code)
        )
        currency = result.scalar_one_or_none()
        if currency is None:
            return None

        if self.redis is not None:
            await self.redis.setex(
                self._cache_key(code),
                self.settings.currency_cache_ttl,
                str(currency.usd_rate),
            )
        return Decimal(currency.usd_rate)

    async def convert(
        self,
        amount: Decimal,
        from_code: str,
        to_code: str,
    ) -> Decimal | None:
        """Convert amount from_code → to_code via USD pivot."""
        from_code = from_code.upper()
        to_code = to_code.upper()
        if from_code == to_code:
            return amount.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

        from_rate = await self.get_usd_rate(from_code)
        to_rate = await self.get_usd_rate(to_code)
        if from_rate is None or to_rate is None or from_rate == 0:
            return None

        # usd_rate is "units of currency per 1 USD"
        amount_usd = amount / from_rate
        converted = amount_usd * to_rate
        return converted.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    async def warm_cache(self) -> int:
        """Load all currency rows into Redis. Returns count warmed."""
        result = await self.session.execute(select(Currency))
        rows = result.scalars().all()
        if self.redis is None:
            return 0
        pipe = self.redis.pipeline()
        for row in rows:
            pipe.setex(
                self._cache_key(row.code),
                self.settings.currency_cache_ttl,
                str(row.usd_rate),
            )
        await pipe.execute()
        return len(rows)

    async def list_rates(self) -> dict[str, str]:
        result = await self.session.execute(select(Currency))
        rows = result.scalars().all()
        return {row.code: str(row.usd_rate) for row in rows}

    @staticmethod
    def serialize_rates(rates: dict[str, str]) -> str:
        return json.dumps(rates)
