"""Celery soft time limits must escape fetch handlers and fail the zone."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

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

    result = scrape_zone_retail.run("se_asia")

    assert result["ok"] is False
    assert result["status"] == "timed_out"
    assert "soft time" in str(result["error"])
    assert recorded[0]["payload"]["status"] == "running"
    assert recorded[-1]["payload"]["status"] == "timed_out"
    assert recorded[-1]["payload"]["ok"] is False
    started_at = recorded[0]["payload"]["started_at"]
    assert isinstance(started_at, str)
    assert started_at.endswith("+00:00")
    assert recorded[-1]["payload"]["started_at"] == started_at
    assert result["started_at"] == started_at


def test_timeout_records_partial_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[dict[str, object]] = []

    def _record(zone: str, payload: dict[str, object], cycle_id: str | None = None) -> None:
        recorded.append(payload)

    def _boom(_zone: str) -> dict[str, object]:
        exc = SoftTimeLimitExceeded()
        exc.scrape_progress = {  # type: ignore[attr-defined]
            "areas": 12,
            "areas_total": 36,
            "discovered": 80,
            "ingested": 40,
            "cities_completed": [{"country": "PH", "city": "Manila"}],
            "cities_not_reached": [{"country": "TH", "city": "Bangkok"}],
        }
        raise exc

    monkeypatch.setattr("app.workers.tasks.zone_already_succeeded", lambda *_a, **_k: False)
    monkeypatch.setattr("app.workers.tasks.record_zone_result", _record)
    monkeypatch.setattr("app.workers.tasks.scrape_and_ingest_zone", _boom)

    result = scrape_zone_retail.run("se_asia")

    assert result["ok"] is False
    assert result["status"] == "timed_out"
    assert result["areas"] == 12
    assert result["areas_total"] == 36
    assert result["discovered"] == 80
    assert result["ingested"] == 40
    assert result["cities_not_reached"] == [{"country": "TH", "city": "Bangkok"}]
    assert recorded[-1]["ingested"] == 40


def test_timed_out_zone_is_not_counted_ok() -> None:
    health = _zone_health(
        {
            "se_asia": {
                "ok": False,
                "status": "timed_out",
                "error": "soft time limit exceeded",
                "areas": 20,
                "areas_total": 36,
                "ingested": 400,
            }
        }
    )
    assert "se_asia" in health["failed"]
    assert health["ok"] == 0
    assert health["timed_out"] == ["se_asia 20/36 cities, 400 ingested"]


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None

    def commit(self) -> None:
        raise AssertionError("session committed after a time limit")


def test_ingest_does_not_swallow_soft_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.scrapers.base import ScrapedDeal
    from app.services.ingest import ingest_hub_scrape, ingest_scraped_deals

    def _boom(_session: object, _scraped: object) -> None:
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr("app.services.ingest.upsert_scraped_deal", _boom)
    deal = ScrapedDeal(
        merchant_name="Pizza Hut Takeaway",
        title="Lunch deal",
        description="Two pizzas",
        raw_url="https://example.com/deals",
        original_price=Decimal("10"),
        deal_price=Decimal("8"),
        currency_code="USD",
        country_code="US",
        city="Phoenix",
    )
    with pytest.raises(SoftTimeLimitExceeded):
        ingest_hub_scrape(_Session(), "US", "Phoenix", [deal])
    with pytest.raises(SoftTimeLimitExceeded):
        ingest_scraped_deals(_Session(), [deal])


def test_city_loop_attaches_partial_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.scrape_runner import scrape_and_ingest_markets

    class FakeScraper:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def scrape(self, _country: str, city: str) -> list[object]:
            if city == "Bangkok":
                raise SoftTimeLimitExceeded()
            return [object(), object(), object()]

    monkeypatch.setattr(
        "app.services.scrape_runner.iter_market_areas",
        lambda _markets: [("PH", "Manila"), ("TH", "Bangkok"), ("TH", "Chiang Mai")],
    )
    monkeypatch.setattr("app.services.scrape_runner.GlobalRetailScraper", FakeScraper)
    monkeypatch.setattr(
        "app.services.scrape_runner.breakdown_from_scraped_deals",
        lambda _deals: [],
    )
    monkeypatch.setattr("app.services.scrape_runner._Session", lambda: _Session())
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_hub_scrape",
        lambda *_a, **_k: {"ingested": 2, "stale_deactivated": 1},
    )
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_marketing_contacts_from_deals",
        lambda *_a, **_k: 1,
    )
    monkeypatch.setattr(
        "app.services.scrape_runner._live_revalidate",
        lambda *_a, **_k: {"skipped": True},
    )

    with pytest.raises(SoftTimeLimitExceeded) as caught:
        scrape_and_ingest_markets(["PH", "TH"])

    progress = caught.value.scrape_progress  # type: ignore[attr-defined]
    assert progress["areas"] == 1
    assert progress["areas_total"] == 3
    assert progress["discovered"] == 3
    assert progress["ingested"] == 2
    assert progress["cities_completed"] == [{"country": "PH", "city": "Manila"}]
    assert progress["cities_not_reached"] == [
        {"country": "TH", "city": "Bangkok"},
        {"country": "TH", "city": "Chiang Mai"},
    ]


def test_committed_city_counts_when_later_work_hits_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ingest commits before marketing. A limit there must keep that city's totals."""
    from app.services.scrape_runner import scrape_and_ingest_markets

    class FakeScraper:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def scrape(self, _country: str, _city: str) -> list[object]:
            return [object(), object()]

    def _marketing(*_args: object, **_kwargs: object) -> int:
        raise SoftTimeLimitExceeded()

    monkeypatch.setattr(
        "app.services.scrape_runner.iter_market_areas",
        lambda _markets: [("PH", "Manila"), ("TH", "Bangkok")],
    )
    monkeypatch.setattr("app.services.scrape_runner.GlobalRetailScraper", FakeScraper)
    monkeypatch.setattr(
        "app.services.scrape_runner.breakdown_from_scraped_deals",
        lambda _deals: [],
    )
    monkeypatch.setattr("app.services.scrape_runner._Session", lambda: _Session())
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_hub_scrape",
        lambda *_a, **_k: {"ingested": 2, "stale_deactivated": 0},
    )
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_marketing_contacts_from_deals",
        _marketing,
    )

    with pytest.raises(SoftTimeLimitExceeded) as caught:
        scrape_and_ingest_markets(["PH", "TH"])

    progress = caught.value.scrape_progress  # type: ignore[attr-defined]
    assert progress["areas"] == 1
    assert progress["ingested"] == 2
    assert progress["discovered"] == 2
    assert progress["cities_completed"] == [{"country": "PH", "city": "Manila"}]
    assert progress["cities_not_reached"] == [{"country": "TH", "city": "Bangkok"}]


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _handler_propagates(handler: ast.ExceptHandler) -> bool:
    caught = handler.name
    for node in ast.walk(handler):
        if isinstance(node, ast.Call) and _call_name(node) == "reraise_if_fatal":
            return True
        if isinstance(node, ast.Raise):
            if node.exc is None:
                return True
            if (
                caught
                and isinstance(node.exc, ast.Name)
                and node.exc.id == caught
            ):
                return True
    return False


def _catches_broadly(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    names: list[str] = []
    node: ast.expr = handler.type
    if isinstance(node, ast.Tuple):
        parts = list(node.elts)
    else:
        parts = [node]
    for part in parts:
        if isinstance(part, ast.Name):
            names.append(part.id)
        elif isinstance(part, ast.Attribute):
            names.append(part.attr)
    return "Exception" in names or "BaseException" in names


def test_scrape_path_does_not_swallow_soft_time_limit() -> None:
    root = Path(__file__).resolve().parents[1]
    files = [
        *sorted((root / "app" / "scrapers").rglob("*.py")),
        root / "app" / "services" / "ingest.py",
        root / "app" / "services" / "scrape_runner.py",
        root / "app" / "services" / "marketing_contacts.py",
        root / "app" / "services" / "frontend_revalidate.py",
        root / "app" / "services" / "scrape_cycle_stats.py",
        root / "app" / "workers" / "tasks.py",
    ]
    swallowed: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if not _catches_broadly(node):
                continue
            if _handler_propagates(node):
                continue
            swallowed.append(f"{path.relative_to(root)}:{node.lineno}")
    assert swallowed == []
