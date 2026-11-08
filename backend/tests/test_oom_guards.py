"""Guards for the 256 MB Postgres OOM and the Vercel CPU storm."""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.params import Query as QueryParam

from app.api.v1.endpoints.deals import deals_feed
from app.core.config import get_settings
from app.core.database import _connect_args, engine
from app.core.ttl_cache import TtlCache
from app.services.deal_expiry import (
    ExpiredDeal,
    is_publicly_listed,
    revalidate_kwargs_for_expired,
)
from app.services.frontend_revalidate import revalidation_plan
from app.services.scrape_runner import _engine as scrape_engine
from app.workers.tasks import _sync_engine

_BACKEND = Path(__file__).resolve().parents[1]


def test_api_pool_is_smaller_and_recycles() -> None:
    pool = engine.pool
    settings = get_settings()
    if settings.is_production:
        assert pool.size() == 3
        assert pool._max_overflow == 2
    else:
        assert pool.size() == 10
        assert pool._max_overflow == 20
    assert pool._recycle == 1800
    assert pool._timeout == 10
    assert _connect_args["statement_cache_size"] == 16
    assert _connect_args["prepared_statement_cache_size"] == 16


def test_asyncpg_accepts_statement_cache_size() -> None:
    """Both caches are 16, and asyncpg.connect never sees SQLAlchemy's key.

    SQLAlchemy 2.0.36 pops prepared_statement_cache_size inside
    AsyncAdapt_asyncpg_dbapi.connect and stores it on the adapter LRU.
    asyncpg 0.30 has no **kwargs, so that name must not be forwarded.
    """
    import sqlalchemy.dialects.postgresql.asyncpg as sa_asyncpg

    signature = inspect.signature(asyncpg.connect)
    assert "statement_cache_size" in signature.parameters
    assert "prepared_statement_cache_size" not in signature.parameters
    signature.bind(statement_cache_size=_connect_args["statement_cache_size"])
    with pytest.raises(TypeError):
        signature.bind(prepared_statement_cache_size=16)

    captured: dict[str, object] = {}
    adapters: list[sa_asyncpg.AsyncAdapt_asyncpg_connection] = []
    original_init = sa_asyncpg.AsyncAdapt_asyncpg_connection.__init__

    def _init(
        self: sa_asyncpg.AsyncAdapt_asyncpg_connection,
        dbapi: object,
        connection: object,
        prepared_statement_cache_size: int = 100,
        prepared_statement_name_func: object = None,
    ) -> None:
        adapters.append(self)
        original_init(
            self,
            dbapi,
            connection,
            prepared_statement_cache_size,
            prepared_statement_name_func,
        )

    async def _capture(*_args: object, **kwargs: object) -> object:
        captured["kwargs"] = kwargs
        return object()

    original_connect = asyncpg.connect
    asyncpg.connect = _capture  # type: ignore[method-assign]
    sa_asyncpg.AsyncAdapt_asyncpg_connection.__init__ = _init  # type: ignore[method-assign]

    async def _open() -> None:
        try:
            async with engine.connect() as _conn:
                pass
        except Exception:
            return

    try:
        asyncio.run(_open())
    finally:
        asyncpg.connect = original_connect  # type: ignore[method-assign]
        sa_asyncpg.AsyncAdapt_asyncpg_connection.__init__ = original_init  # type: ignore[method-assign]

    kwargs = captured["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["statement_cache_size"] == 16
    assert "prepared_statement_cache_size" not in kwargs
    signature.bind(**kwargs)

    assert adapters, "SQLAlchemy did not build an asyncpg adapter"
    cache = adapters[0]._prepared_statement_cache
    assert cache is not None
    assert cache.capacity == 16


def test_worker_pools_stay_tiny() -> None:
    assert _sync_engine.pool.size() == 1
    assert _sync_engine.pool._max_overflow == 1
    assert _sync_engine.pool._recycle == 1800
    assert scrape_engine.pool.size() == 1
    assert scrape_engine.pool._max_overflow == 1
    assert scrape_engine.pool._recycle == 1800


def test_city_revalidation_does_not_bust_the_whole_site() -> None:
    plan = revalidation_plan({("GB", "Manchester"), ("US", "New York")})
    assert "deals" not in plan["tags"]
    assert "/" not in plan["paths"]
    assert "deals-uk-manchester" in plan["tags"]
    assert "deals-us-new-york" in plan["tags"]
    assert "/uk/manchester" in plan["paths"]
    assert "/us/new-york" in plan["paths"]
    assert "/uk" in plan["paths"]
    assert "/us" in plan["paths"]


def test_global_revalidation_is_opt_in() -> None:
    plan = revalidation_plan(set(), include_global=True)
    assert plan == {"tags": ["deals"], "paths": ["/"]}

    scoped = revalidation_plan({("IE", "Dublin")}, include_global=True)
    assert scoped["tags"][0] == "deals"
    assert scoped["paths"][0] == "/"
    assert "deals-ie-dublin" in scoped["tags"]
    assert "/ie/dublin" in scoped["paths"]


def test_public_feed_does_not_default_to_auto_scrape() -> None:
    default = inspect.signature(deals_feed).parameters["auto_scrape"].default
    assert isinstance(default, QueryParam)
    assert default.default is False
    source = (_BACKEND / "app" / "api" / "v1" / "endpoints" / "deals.py").read_text(
        encoding="utf-8"
    )
    assert "scrape_and_ingest_area" not in source


def test_single_alembic_head() -> None:
    cfg = Config(str(_BACKEND / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["019_new_business_outreach"]


def test_expiry_revalidates_city_and_deal_tags() -> None:
    deal_id = uuid4()
    kwargs = revalidate_kwargs_for_expired(
        [ExpiredDeal(id=deal_id, country_code="GB", city="Manchester")]
    )
    plan = revalidation_plan(
        kwargs["areas"],  # type: ignore[arg-type]
        include_global=True,
        extra_tags=kwargs["extra_tags"],  # type: ignore[arg-type]
    )
    assert "deals" in plan["tags"]
    assert "/" in plan["paths"]
    assert "deals-uk-manchester" in plan["tags"]
    assert "/uk/manchester" in plan["paths"]
    assert f"deal-{deal_id}" in plan["tags"]


def test_public_listing_hides_inactive_and_expired() -> None:
    now = datetime.now(timezone.utc)
    assert is_publicly_listed(
        is_active=True, deleted_at=None, expires_at=None, now=now
    )
    assert not is_publicly_listed(
        is_active=False, deleted_at=None, expires_at=None, now=now
    )
    assert not is_publicly_listed(
        is_active=True,
        deleted_at=None,
        expires_at=now - timedelta(minutes=1),
        now=now,
    )
    assert not is_publicly_listed(
        is_active=True, deleted_at=now, expires_at=None, now=now
    )


def test_ttl_cache_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    cache: TtlCache[str] = TtlCache(10)
    now = 1_000.0
    monkeypatch.setattr("app.core.ttl_cache.time.monotonic", lambda: now)
    cache.set("metrics", "a")
    assert cache.get("metrics") == "a"
    monkeypatch.setattr("app.core.ttl_cache.time.monotonic", lambda: now + 10)
    assert cache.get("metrics") is None


def test_ttl_cache_drops_least_recently_used(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.ttl_cache.time.monotonic", lambda: 50.0)
    cache: TtlCache[str] = TtlCache(60, max_entries=2)
    cache.set("a", "1")
    cache.set("b", "2")
    assert cache.get("a") == "1"
    cache.set("c", "3")
    assert cache.get("b") is None
    assert cache.get("a") == "1"
    assert cache.get("c") == "3"


def test_oom_migration_is_concurrent_and_idempotent() -> None:
    text = (
        _BACKEND / "alembic" / "versions" / "017_oom_feed_indexes.py"
    ).read_text(encoding="utf-8")
    env = (_BACKEND / "alembic" / "env.py").read_text(encoding="utf-8")
    for name in (
        "ix_oom_deals_merchant_active_not_deleted",
        "ix_oom_deals_expires_active",
        "ix_oom_marketing_contacts_lower_business_name",
    ):
        assert name in text
    assert text.count("CREATE INDEX CONCURRENTLY IF NOT EXISTS") == 3
    assert "autocommit_block" in text
    assert "016_newsletter_region" in text
    assert "SET statement_timeout = 0" in text
    assert "SET statement_timeout = 0" in env
    assert "WHERE is_active AND deleted_at IS NULL" in text
    assert "WHERE is_active" in text
    assert "lower(business_name)" in text
