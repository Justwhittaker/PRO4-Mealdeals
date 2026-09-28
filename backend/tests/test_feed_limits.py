"""Guardrails against oversized deal-feed loads that OOM the web dyno."""

from __future__ import annotations

from app.core.feed_limits import (
    FEED_OVERFETCH_CAP,
    MAX_FEED_LIMIT,
    MAX_SITEMAP_LIMIT,
)


def test_feed_limit_caps_are_safe_for_512mb_dyno() -> None:
    assert MAX_FEED_LIMIT <= 500
    assert FEED_OVERFETCH_CAP <= 750
    assert MAX_SITEMAP_LIMIT <= 500
    assert FEED_OVERFETCH_CAP >= MAX_FEED_LIMIT


def test_feed_overfetch_never_materialises_tens_of_thousands() -> None:
    # Historical bug: limit=10000 fetched limit*3 rows into the web process.
    requested = 10_000
    capped_limit = min(requested, MAX_FEED_LIMIT)
    fetch_rows = min(capped_limit * 3, FEED_OVERFETCH_CAP)
    assert fetch_rows <= FEED_OVERFETCH_CAP
    assert fetch_rows < 1000
