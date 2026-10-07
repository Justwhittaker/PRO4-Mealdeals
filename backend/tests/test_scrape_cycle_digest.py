"""Unit tests for scrape cycle digest formatting / cycle windows."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.services.scrape_cycle_digest import (
    _zone_health,
    build_cycle_digest_report,
    format_digest_body,
)
from app.services.scrape_cycle_stats import (
    cycle_id_from_task_request,
    cycle_start_for_time,
    digest_cycle_start,
    record_zone_result,
    zone_already_succeeded,
)


def test_cycle_start_for_time_picks_latest_base() -> None:
    now = datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc)
    start = cycle_start_for_time(now)
    assert start == datetime(2026, 9, 21, 6, 0, tzinfo=timezone.utc)

    evening = datetime(2026, 9, 21, 19, 10, tzinfo=timezone.utc)
    assert cycle_start_for_time(evening) == datetime(
        2026, 9, 21, 18, 0, tzinfo=timezone.utc
    )

    early = datetime(2026, 9, 21, 3, 0, tzinfo=timezone.utc)
    assert cycle_start_for_time(early) == datetime(
        2026, 9, 20, 18, 0, tzinfo=timezone.utc
    )


def test_digest_cycle_start_maps_beat_slots() -> None:
    morning = datetime(2026, 9, 21, 5, 50, tzinfo=timezone.utc)
    assert digest_cycle_start(morning) == datetime(
        2026, 9, 20, 18, 0, tzinfo=timezone.utc
    )
    evening = datetime(2026, 9, 21, 17, 50, tzinfo=timezone.utc)
    assert digest_cycle_start(evening) == datetime(
        2026, 9, 21, 6, 0, tzinfo=timezone.utc
    )


def test_format_digest_body_includes_requested_sections() -> None:
    body = format_digest_body(
        {
            "cycle_id": "2026-09-21T06",
            "since_label": "2026-09-21 06:00",
            "zones": {
                "total_zones": 8,
                "completed": 7,
                "ok": 7,
                "failed": [],
                "missing": ["western_europe"],
                "pct_completed": 87.5,
                "pct_ok": 87.5,
                "large_families": [
                    {
                        "family": "north_america",
                        "label": "North America & Caribbean (large)",
                        "pct_completed": 100.0,
                        "completed": 2,
                        "total": 2,
                    },
                    {
                        "family": "western_europe",
                        "label": "Western Europe (large)",
                        "pct_completed": 66.7,
                        "completed": 2,
                        "total": 3,
                    },
                ],
            },
            "site": {
                "healthy": True,
                "api_ok": True,
                "frontend_ok": True,
                "revalidate_ok": 40,
                "revalidate_fail": 2,
                "revalidate_pct": 95.2,
                "detail": "ok",
            },
            "new_deals": 12,
            "dropped_deals": 5,
            "net_new_emails": 9,
            "categories": [
                ("Restaurants, Cafe's & Bistro's", 100, 40.0),
                ("Hotels, Resorts & B&B's", 50, 20.0),
            ],
        }
    )
    assert "Zones: 88% completed" in body
    assert "Missing: western_europe" in body
    assert "Large · North America & Caribbean (large): 100%" in body
    assert "Large · Western Europe (large): 67%" in body
    assert "Site transfer: OK" in body
    assert "New deals: 12" in body
    assert "Dropped deals: 5" in body
    assert "Net new merchant emails: 9" in body
    assert "Category mix" in body
    assert "Restaurants" in body


def test_crashed_and_running_zones_are_failed_not_ok() -> None:
    health = _zone_health(
        {
            "asia": {
                "ok": False,
                "status": "failed",
                "error": "Invalid IPv6 URL",
            },
            "us": {"ok": False, "status": "running"},
            "oceania": {"ok": True, "status": "completed"},
        }
    )
    assert set(health["failed"]) == {"asia", "us"}
    assert "oceania" not in health["failed"]
    assert health["ok"] == 1
    assert health["completed"] == 2
    assert "us" not in health["missing"]


def test_digest_does_not_mark_db_activity_as_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest.load_cycle_zone_results",
        lambda _cycle_id: {
            "asia": {"ok": False, "status": "failed", "error": "Invalid IPv6 URL"},
        },
    )
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest._query_window_counts",
        lambda _engine, _since: {
            "new_deals": 3,
            "dropped_deals": 0,
            "net_new_emails": 1,
            "new_email_rows": 1,
            "gained_email_rows": 0,
            "active_scraped_deals": 10,
        },
    )
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest._category_breakdown",
        lambda _engine: [],
    )
    monkeypatch.setattr("app.services.scrape_cycle_digest._engine", lambda: object())
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest._site_transfer_health",
        lambda **_kwargs: {
            "healthy": True,
            "api_ok": True,
            "frontend_ok": True,
            "revalidate_ok": 0,
            "revalidate_fail": 0,
            "revalidate_pct": None,
            "detail": "ok",
        },
    )

    report = build_cycle_digest_report(
        datetime(2026, 9, 21, 17, 50, tzinfo=timezone.utc)
    )
    assert "asia" in report["zones"]["failed"]
    assert report["zones"]["ok"] == 0
    assert "us" in report["zones"]["missing"]
    assert "asia" not in report["zones"]["missing"]
    body = format_digest_body(report)
    assert "Failed: asia" in body
    assert "100% ok" not in body


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)


def test_zone_result_keeps_the_queued_cycle_id(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    cycle_id = record_zone_result(
        "us",
        {"ok": False, "status": "failed", "error": "Invalid IPv6 URL"},
        cycle_id="2026-09-19T06",
    )
    assert cycle_id == "2026-09-19T06"
    stored = next(iter(fake.values.values()))
    payload = json.loads(stored)
    assert payload["cycle_id"] == "2026-09-19T06"
    assert "2026-09-19T06" in next(iter(fake.values))
    assert zone_already_succeeded("2026-09-19T06", "us") is False

    record_zone_result(
        "us",
        {"ok": True, "status": "completed"},
        cycle_id="2026-09-19T06",
    )
    assert zone_already_succeeded("2026-09-19T06", "us") is True

    record_zone_result(
        "asia",
        {"ok": False, "status": "running"},
        cycle_id="2026-09-19T06",
    )
    assert zone_already_succeeded("2026-09-19T06", "asia") is False


def test_cycle_id_is_read_from_the_queued_message() -> None:
    class _Request:
        scrape_cycle_id = "2026-09-21T18"
        headers = {"scrape_cycle_id": "ignored"}

    assert cycle_id_from_task_request(_Request()) == "2026-09-21T18"

    class _HeadersOnly:
        headers = {"scrape_cycle_id": "2026-09-21T06"}

    assert cycle_id_from_task_request(_HeadersOnly()) == "2026-09-21T06"
    assert cycle_id_from_task_request(None) is None
