"""Guards for the 256 MB Postgres OOM and the Vercel CPU storm."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from fastapi.params import Query as QueryParam

from app.api.v1.endpoints.deals import deals_feed
from app.core.config import get_settings
from app.core.database import _connect_args, engine
from app.core.ttl_cache import TtlCache
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
    assert _connect_args["prepared_statement_cache_size"] == 16


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


def test_ttl_cache_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    cache: TtlCache[str] = TtlCache(10)
    now = 1_000.0
    monkeypatch.setattr("app.core.ttl_cache.time.monotonic", lambda: now)
    cache.set("metrics", "a")
    assert cache.get("metrics") == "a"
    monkeypatch.setattr("app.core.ttl_cache.time.monotonic", lambda: now + 10)
    assert cache.get("metrics") is None


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
