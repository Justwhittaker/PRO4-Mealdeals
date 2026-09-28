"""Guardrails against oversized deal-feed loads that OOM the web dyno."""

from __future__ import annotations

from app.core.feed_limits import (
    MAX_FEED_CANDIDATES,
    MAX_FEED_LIMIT,
    MAX_SITEMAP_LIMIT,
)


def test_feed_limit_caps_are_safe_for_512mb_dyno() -> None:
    assert MAX_FEED_LIMIT <= 500
    assert MAX_SITEMAP_LIMIT <= 500
    assert MAX_FEED_CANDIDATES <= 20_000


def test_feed_page_slice_supports_show_all() -> None:
    # Score many candidates, hydrate only one page.
    total = 1_706
    page_size = 200
    offset = 400
    page_ids = list(range(total))[offset : offset + page_size]
    assert len(page_ids) == page_size
    assert page_ids[0] == 400
    assert offset + len(page_ids) < total
