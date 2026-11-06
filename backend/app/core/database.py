"""Async SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

_connect_args: dict = {
    # asyncpg.connect kwarg (default 100). Not prepared_statement_cache_size:
    # that name is SQLAlchemy's, and asyncpg 0.30 rejects it with TypeError.
    # 16 caps server-side plans on each backend. Not zero, so a hot
    # connection can still reuse a plan. PgBouncer is not in front.
    "statement_cache_size": 16,
}
if settings.database_requires_ssl:
    # asyncpg uses a boolean SSL flag (Render external hostnames require TLS).
    _connect_args["ssl"] = True

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    # 256 MB Postgres: keep the resident pool small. Do not raise these.
    # Production was 5+5. Dev stays larger so local tests are not starved.
    pool_size=3 if settings.is_production else 10,
    max_overflow=2 if settings.is_production else 20,
    # Recycle backends so asyncpg's server-side plans do not live all day.
    pool_recycle=1800,
    pool_timeout=10,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependencies."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
