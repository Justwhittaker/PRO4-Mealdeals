"""Celery soft time limits must escape fetch handlers and fail the zone."""

from __future__ import annotations

import pytest
from celery.exceptions import SoftTimeLimitExceeded

from app.scrapers.fetch_guard import SpeculativeFetchGuard
from app.scrapers.global_retail import GlobalRetailScraper
from app.scrapers.offer_links import resolve_offer_url
from app.scrapers.overpass_client import fetch_overpass_direct
from app.services.scrape_cycle_digest import _zone_health
from app.workers.tasks import scrape_zone_retail


@pytest.mark.asyncio
async def test_resolve_offer_url_propagates_soft_time_limit() -> None:
    calls: list[str] = []

    async def _fetch(url: str) -> str:
        calls.append(url)
        raise SoftTimeLimitExceeded()

    with pytest.raises(SoftTimeLimitExceeded):
        await resolve_offer_url(
            "https://bistro.example/",
            _fetch,
            parse_soup=lambda _html: None,
            max_extra_fetches=4,
            guard=SpeculativeFetchGuard(),
        )
    assert calls == ["https://bistro.example/"]


@pytest.mark.asyncio
async def test_live_parse_propagates_soft_time_limit() -> None:
    scraper = GlobalRetailScraper()
    calls: list[str] = []

    async def _fetch(url: str) -> str:
        calls.append(url)
        raise SoftTimeLimitExceeded()

    scraper.fetch_html = _fetch  # type: ignore[method-assign]
    with pytest.raises(SoftTimeLimitExceeded):
        await scraper._try_live_parse("https://bistro.example/deals", "Bistro")
    assert calls == ["https://bistro.example/deals"]
    assert scraper._live_cache == {}


@pytest.mark.asyncio
async def test_site_media_propagates_soft_time_limit() -> None:
    scraper = GlobalRetailScraper()
    calls: list[str] = []

    async def _fetch(url: str) -> str:
        calls.append(url)
        raise SoftTimeLimitExceeded()

    scraper.fetch_html = _fetch  # type: ignore[method-assign]
    with pytest.raises(SoftTimeLimitExceeded):
        await scraper._fetch_site_media("https://bistro.example/menu")
    assert calls == ["https://bistro.example/"]


@pytest.mark.asyncio
async def test_local_discovery_propagates_soft_time_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom(_country: str, _city: str) -> list:
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr("app.scrapers.global_retail.discover_local_venues", _boom)
    scraper = GlobalRetailScraper()
    with pytest.raises(SoftTimeLimitExceeded):
        await scraper.scrape("MY", "Kuala Lumpur")


@pytest.mark.asyncio
async def test_overpass_propagates_soft_time_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_args: object) -> bool:
            return False

        async def post(self, *_args: object, **_kwargs: object) -> object:
            raise SoftTimeLimitExceeded()

    monkeypatch.setattr("app.scrapers.overpass_client.httpx.AsyncClient", _Client)
    with pytest.raises(SoftTimeLimitExceeded):
        await fetch_overpass_direct("[out:json];", timeout=1, log_label="test")


def test_soft_time_limit_records_the_zone_as_timed_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, object]] = []

    def _record(zone: str, payload: dict[str, object], cycle_id: str | None = None) -> None:
        recorded.append({"zone": zone, "payload": payload, "cycle_id": cycle_id})

    def _boom(_zone: str) -> dict[str, object]:
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr("app.workers.tasks.zone_already_succeeded", lambda *_a, **_k: False)
    monkeypatch.setattr("app.workers.tasks.record_zone_result", _record)
    monkeypatch.setattr("app.workers.tasks.scrape_and_ingest_zone", _boom)

    result = scrape_zone_retail.run("asia")

    assert result["ok"] is False
    assert result["status"] == "timed_out"
    assert "soft time" in str(result["error"])
    assert recorded[0]["payload"]["status"] == "running"
    assert recorded[-1]["payload"]["status"] == "timed_out"
    assert recorded[-1]["payload"]["ok"] is False


def test_timed_out_zone_is_not_counted_ok() -> None:
    health = _zone_health(
        {
            "asia": {
                "ok": False,
                "status": "timed_out",
                "error": "soft time limit exceeded",
            }
        }
    )
    assert "asia" in health["failed"]
    assert health["ok"] == 0
