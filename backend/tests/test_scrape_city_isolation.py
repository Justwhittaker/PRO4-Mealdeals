"""One bad href or one failing city must not abort the rest of a zone."""

from __future__ import annotations

import pytest

from app.scrapers.global_retail import GlobalRetailScraper
from app.services.scrape_runner import scrape_and_ingest_markets


class _Session:
    def __enter__(self) -> _Session:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def test_failing_city_does_not_abort_later_cities(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    class FakeScraper:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def scrape(self, country: str, city: str) -> list:
            seen.append(city)
            if city == "Kuala Lumpur":
                raise ValueError("Invalid IPv6 URL")
            return []

    monkeypatch.setattr(
        "app.services.scrape_runner.iter_market_areas",
        lambda _markets: [("MY", "Kuala Lumpur"), ("MY", "Penang"), ("SG", "Singapore")],
    )
    monkeypatch.setattr("app.services.scrape_runner.GlobalRetailScraper", FakeScraper)
    monkeypatch.setattr("app.services.scrape_runner._Session", lambda: _Session())
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_hub_scrape",
        lambda *_args, **_kwargs: {"ingested": 0, "stale_deactivated": 0},
    )
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_marketing_contacts_from_deals",
        lambda *_args, **_kwargs: 0,
    )
    monkeypatch.setattr(
        "app.services.scrape_runner._live_revalidate",
        lambda *_args, **_kwargs: {"skipped": True},
    )
    monkeypatch.setattr(
        "app.services.scrape_runner.build_scrape_report",
        lambda *_args, **_kwargs: {
            "summary": {"marketing_contacts_unique": 0},
            "breakdown": [],
            "category_tally": [],
        },
    )

    result = scrape_and_ingest_markets(["MY", "SG"])

    assert seen == ["Kuala Lumpur", "Penang", "Singapore"]
    assert result["cities_failed"] == [
        {
            "country": "MY",
            "city": "Kuala Lumpur",
            "error": "Invalid IPv6 URL",
        }
    ]
    assert result["areas"] == 3


def test_city_failure_rolls_back_before_the_next_city(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class RecordingSession:
        def rollback(self) -> None:
            events.append("rollback")

        def close(self) -> None:
            events.append("close")

    class FakeScraper:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def scrape(self, _country: str, city: str) -> list:
            events.append(f"scrape:{city}")
            return []

    def _ingest(_session: object, _country: str, city: str, _deals: object) -> dict[str, int]:
        events.append(f"ingest:{city}")
        if city == "Tampa":
            raise RuntimeError(
                "Can't reconnect until invalid transaction is rolled back"
            )
        return {"ingested": 0, "stale_deactivated": 0}

    monkeypatch.setattr("app.services.scrape_runner._Session", RecordingSession)
    monkeypatch.setattr(
        "app.services.scrape_runner.iter_market_areas",
        lambda _markets: [("US", "Tampa"), ("US", "Seattle")],
    )
    monkeypatch.setattr("app.services.scrape_runner.GlobalRetailScraper", FakeScraper)
    monkeypatch.setattr("app.services.scrape_runner.ingest_hub_scrape", _ingest)
    monkeypatch.setattr(
        "app.services.scrape_runner.ingest_marketing_contacts_from_deals",
        lambda *_args, **_kwargs: 0,
    )
    monkeypatch.setattr(
        "app.services.scrape_runner._live_revalidate",
        lambda *_args, **_kwargs: {"skipped": True},
    )
    monkeypatch.setattr(
        "app.services.scrape_runner.build_scrape_report",
        lambda *_args, **_kwargs: {
            "summary": {"marketing_contacts_unique": 0},
            "breakdown": [],
            "category_tally": [],
        },
    )

    result = scrape_and_ingest_markets(["US"])

    assert [item["city"] for item in result["cities_failed"]] == ["Tampa"]
    assert "scrape:Seattle" in events
    assert "ingest:Seattle" in events
    assert events.index("rollback") < events.index("close")
    assert events.index("close") < events.index("ingest:Seattle")


def test_time_limit_still_aborts_the_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    class SoftTimeLimitExceeded(Exception):
        pass

    class FakeScraper:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        async def scrape(self, _country: str, city: str) -> list:
            raise SoftTimeLimitExceeded(city)

    monkeypatch.setattr(
        "app.services.scrape_runner.iter_market_areas",
        lambda _markets: [("US", "Phoenix"), ("US", "Dallas")],
    )
    monkeypatch.setattr("app.services.scrape_runner.GlobalRetailScraper", FakeScraper)
    monkeypatch.setattr("app.services.scrape_runner._Session", lambda: _Session())
    monkeypatch.setattr(
        "app.services.scrape_runner.build_scrape_report",
        lambda *_args, **_kwargs: {
            "summary": {"marketing_contacts_unique": 0},
            "breakdown": [],
            "category_tally": [],
        },
    )

    with pytest.raises(SoftTimeLimitExceeded):
        scrape_and_ingest_markets(["US"])


@pytest.mark.asyncio
async def test_one_bad_source_does_not_drop_the_rest_of_the_city(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _no_local(_country: str, _city: str) -> list:
        return []

    async def _parse(self: GlobalRetailScraper, url: str, merchant: str, **_kwargs: object) -> dict:
        if merchant == "Bad Elementor":
            raise ValueError(
                "'elementor-template%20id=2073' does not appear to be an IPv4 or IPv6 address"
            )
        return {"offer_url": url, "title": f"{merchant}: Lunch deal"}

    monkeypatch.setattr("app.scrapers.global_retail.discover_local_venues", _no_local)
    monkeypatch.setattr(
        "app.scrapers.global_retail.MARKET_SOURCES",
        {
            "MY": [
                {"merchant": "Bad Elementor", "url": "https://bad.example/"},
                {"merchant": "Good Bistro", "url": "https://good.example/deals"},
            ]
        },
    )
    monkeypatch.setattr(
        "app.scrapers.global_retail.resolve_dish_placeholder",
        lambda **_kwargs: ("https://example.com/lunch.jpg", "lunch"),
    )
    monkeypatch.setattr(GlobalRetailScraper, "_try_live_parse", _parse)

    scraper = GlobalRetailScraper()
    deals = await scraper.scrape("MY", "Kuala Lumpur")
    assert [deal.merchant_name for deal in deals] == ["Good Bistro"]
