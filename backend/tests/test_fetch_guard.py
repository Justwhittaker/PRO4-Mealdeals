"""Speculative probes skip dead, parked, and already-missed hosts."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from app.scrapers.fetch_guard import (
    HOST_SKIP_TTL_SECONDS,
    PARKED_OBSERVATIONS_BEFORE_SKIP,
    TRANSPORT_FAILURES_BEFORE_SKIP,
    SpeculativeFetchGuard,
    looks_parked_html,
)
from app.scrapers.global_retail import GlobalRetailScraper
from app.scrapers.offer_links import resolve_offer_url

_DNS = OSError("[Errno -2] Name or service not known")


def _dns(guard: SpeculativeFetchGuard, url: str = "https://dead.example/deals") -> bool:
    return guard.note_error(url, _DNS, speculative=True)


def test_one_dns_failure_stops_the_burst_but_does_not_hide_the_host() -> None:
    guard = SpeculativeFetchGuard()
    assert _dns(guard, "https://Dead.Example/deals") is True
    assert guard.should_skip("https://dead.example/offers", speculative=True) is None
    assert guard.should_skip("https://dead.example/", speculative=False) is None
    assert guard.should_skip("https://alive.example/deals", speculative=True) is None


def test_repeated_dns_failures_skip_guessed_paths_not_the_primary_page() -> None:
    guard = SpeculativeFetchGuard()
    for _ in range(TRANSPORT_FAILURES_BEFORE_SKIP - 1):
        _dns(guard)
    assert guard.should_skip("https://dead.example/offers", speculative=True) is None
    _dns(guard)
    assert guard.should_skip("https://dead.example/offers", speculative=True) == "dns_or_ssl"
    assert guard.should_skip("https://dead.example/", speculative=False) is None
    assert guard.should_skip("https://alive.example/deals", speculative=True) is None


def test_later_success_clears_a_dead_host_including_the_primary_page() -> None:
    guard = SpeculativeFetchGuard()
    for _ in range(TRANSPORT_FAILURES_BEFORE_SKIP):
        _dns(guard)
    assert guard.should_skip("https://dead.example/offers", speculative=True) == "dns_or_ssl"

    guard.note_success(
        "https://dead.example/",
        html="<html><h1>Lunch deal</h1>" + ("menu " * 40),
    )
    assert guard.should_skip("https://dead.example/offers", speculative=True) is None
    assert guard.should_skip("https://dead.example/", speculative=False) is None
    # The strike counter resets, so one more blip does not hide the host again.
    _dns(guard)
    assert guard.should_skip("https://dead.example/offers", speculative=True) is None


def test_ssl_failure_counts_toward_the_same_dead_mark() -> None:
    guard = SpeculativeFetchGuard()
    exc = OSError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    for _ in range(TRANSPORT_FAILURES_BEFORE_SKIP):
        assert guard.note_error("https://expired.example/", exc, speculative=False) is True
    assert guard.should_skip("https://expired.example/specials", speculative=True) == "dns_or_ssl"
    assert guard.should_skip("https://expired.example/", speculative=False) is None


def test_speculative_404_is_cached_but_configured_url_is_not_skipped() -> None:
    class _Response:
        status_code = 404

    class _HttpError(Exception):
        def __init__(self) -> None:
            super().__init__("404")
            self.response = _Response()

    guard = SpeculativeFetchGuard()
    assert (
        guard.note_error(
            "https://bistro.example/deals",
            _HttpError(),
            speculative=True,
        )
        is False
    )
    assert guard.should_skip("https://bistro.example/deals", speculative=True) == "cached_miss"
    assert guard.should_skip("https://bistro.example/deals", speculative=False) is None
    assert guard.should_skip("https://bistro.example/offers/lunch", speculative=True) is None


def test_parked_html_needs_a_repeat_before_guessed_paths_are_skipped() -> None:
    guard = SpeculativeFetchGuard()
    html = "<html><title>This domain is for sale</title><p>Buy this domain</p></html>"
    assert looks_parked_html(html) is True
    assert guard.note_html("https://parked.example/", html) is False
    assert guard.should_skip("https://parked.example/promotions", speculative=True) is None
    for _ in range(PARKED_OBSERVATIONS_BEFORE_SKIP - 1):
        guard.note_html("https://parked.example/deals", html)
    assert guard.should_skip("https://parked.example/promotions", speculative=True) == "parked"
    assert guard.should_skip("https://parked.example/", speculative=False) is None


def test_real_page_clears_a_parked_mark() -> None:
    guard = SpeculativeFetchGuard()
    parked = "<html><title>This domain is for sale</title><p>Buy this domain</p></html>"
    for _ in range(PARKED_OBSERVATIONS_BEFORE_SKIP):
        guard.note_html("https://parked.example/", parked)
    assert guard.should_skip("https://parked.example/deals", speculative=True) == "parked"
    guard.note_success(
        "https://parked.example/",
        html="<html><h1>Lunch deal 20% off</h1>" + ("special " * 40),
    )
    assert guard.should_skip("https://parked.example/deals", speculative=True) is None


def test_real_offer_page_is_not_parked() -> None:
    html = "<html><h1>Lunch deal 20% off this week</h1><p>Happy hour cocktails</p></html>"
    assert looks_parked_html(html) is False


@pytest.mark.asyncio
async def test_resolve_offer_url_stops_after_dns_and_keeps_a_live_offer() -> None:
    dead_calls: list[str] = []

    async def _dead(url: str) -> str:
        dead_calls.append(url)
        raise OSError("Temporary failure in name resolution")

    dead_guard = SpeculativeFetchGuard()
    found = await resolve_offer_url(
        "https://gone.example/",
        _dead,
        parse_soup=lambda _html: None,
        max_extra_fetches=4,
        guard=dead_guard,
    )
    assert found is None
    assert dead_calls == ["https://gone.example/"]
    assert dead_guard.should_skip("https://gone.example/deals", speculative=True) is None

    async def _live(url: str) -> str:
        if url.rstrip("/").endswith("/offers"):
            return (
                "<html><body><a href='/offers/lunch-special'>"
                "Lunch deal 20% off</a></body></html>" * 5
            )
        raise _NotFound(url)

    class _NotFound(Exception):
        def __init__(self, url: str) -> None:
            super().__init__(url)
            self.response = type("R", (), {"status_code": 404})()

    live_guard = SpeculativeFetchGuard()
    offer = await resolve_offer_url(
        "https://bistro.example/",
        _live,
        parse_soup=lambda html: BeautifulSoup(html, "html.parser"),
        max_extra_fetches=4,
        guard=live_guard,
    )
    assert offer == "https://bistro.example/offers/lunch-special"
    assert (
        live_guard.should_skip("https://bistro.example/deals", speculative=True)
        == "cached_miss"
    )


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key: str) -> int:
        current = self.values.get(key, 0)
        count = int(current) + 1 if not isinstance(current, set) else 1
        self.values[key] = count
        return count

    def expire(self, key: str, ttl: int) -> bool:
        self.ttls[key] = ttl
        return True

    def setex(self, key: str, ttl: int, value: str) -> bool:
        self.values[key] = value
        self.ttls[key] = ttl
        return True

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.values:
                del self.values[key]
                removed += 1
            self.ttls.pop(key, None)
        return removed

    def exists(self, key: str) -> int:
        return 1 if key in self.values else 0

    def smembers(self, key: str) -> set[str]:
        value = self.values.get(key, set())
        if isinstance(value, set):
            return set(value)
        return set()

    def ping(self) -> bool:
        return True


def _guard_backed_by(fake: _FakeRedis) -> SpeculativeFetchGuard:
    guard = SpeculativeFetchGuard(redis_url="redis://fetch-guard-test")
    guard._redis = lambda: fake  # type: ignore[method-assign]
    return guard


def test_dead_mark_ttl_is_hours_and_a_later_success_clears_redis() -> None:
    fake = _FakeRedis()
    guard = _guard_backed_by(fake)
    for _ in range(TRANSPORT_FAILURES_BEFORE_SKIP):
        _dns(guard, "https://blip.example/deals")

    dead_keys = [key for key in fake.values if key.endswith(":dead:blip.example")]
    assert dead_keys
    assert fake.ttls[dead_keys[0]] == HOST_SKIP_TTL_SECONDS
    assert HOST_SKIP_TTL_SECONDS < 7 * 24 * 60 * 60

    other = _guard_backed_by(fake)
    assert other.should_skip("https://blip.example/offers", speculative=True) == "dns_or_ssl"
    other.note_success("https://blip.example/", html="<html><title>Cafe</title></html>")
    revived = _guard_backed_by(fake)
    assert revived.should_skip("https://blip.example/offers", speculative=True) is None


@pytest.mark.asyncio
async def test_primary_page_fetch_clears_a_dead_host() -> None:
    guard = SpeculativeFetchGuard()
    for _ in range(TRANSPORT_FAILURES_BEFORE_SKIP):
        _dns(guard, "https://blip.example/deals")
    assert guard.should_skip("https://blip.example/offers", speculative=True) == "dns_or_ssl"

    scraper = GlobalRetailScraper()
    scraper._fetch_guard = guard

    async def _fetch(_url: str) -> str:
        return (
            "<html><head><title>Cafe lunch</title></head><body>"
            + ("soup " * 80)
            + "</body></html>"
        )

    scraper.fetch_html = _fetch  # type: ignore[method-assign]
    await scraper._try_live_parse("https://blip.example/", "Blip")
    assert guard.should_skip("https://blip.example/offers", speculative=True) is None
