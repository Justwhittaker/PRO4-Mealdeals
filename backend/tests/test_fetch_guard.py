"""Speculative probes skip dead, parked, and already-missed hosts."""

from __future__ import annotations

import pytest

from app.scrapers.fetch_guard import SpeculativeFetchGuard, looks_parked_html
from app.scrapers.offer_links import resolve_offer_url


def test_dns_failure_blocks_later_urls_on_that_host() -> None:
    guard = SpeculativeFetchGuard()
    assert (
        guard.note_error(
            "https://Dead.Example/deals",
            OSError("[Errno -2] Name or service not known"),
            speculative=True,
        )
        is True
    )
    assert guard.should_skip("https://dead.example/offers", speculative=True) == "dns_or_ssl"
    assert guard.should_skip("https://dead.example/", speculative=False) == "dns_or_ssl"
    assert guard.should_skip("https://alive.example/deals", speculative=True) is None


def test_ssl_failure_is_treated_as_a_dead_host() -> None:
    guard = SpeculativeFetchGuard()
    exc = OSError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
    assert guard.note_error("https://expired.example/", exc, speculative=False) is True
    assert guard.should_skip("https://expired.example/specials", speculative=True) == "dns_or_ssl"


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


def test_parked_html_blocks_the_host() -> None:
    guard = SpeculativeFetchGuard()
    html = "<html><title>This domain is for sale</title><p>Buy this domain</p></html>"
    assert looks_parked_html(html) is True
    assert guard.note_html("https://parked.example/", html) is True
    assert guard.should_skip("https://parked.example/promotions", speculative=True) == "parked"


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

    from bs4 import BeautifulSoup

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
