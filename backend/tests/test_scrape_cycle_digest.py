"""Unit tests for scrape cycle digest formatting / cycle windows."""

from __future__ import annotations

import fnmatch
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.scrapers.zones import ZONE_ORDER, ZONE_TASK_TIME_LIMIT_SECONDS
from app.services.scrape_cycle_digest import (
    _RUNNING_GRACE_SECONDS,
    _query_window_counts,
    _zone_health,
    build_cycle_digest_report,
    format_digest_body,
)
from app.services.scrape_cycle_stats import (
    cycle_id_from_task_request,
    cycle_start_for_time,
    digest_cycle_start,
    load_cycle_zone_results,
    load_cycle_zone_set,
    record_zone_result,
    remember_cycle_zone_set,
    zone_already_succeeded,
)
from app.workers.celery_app import _stamp_scrape_cycle_id
from app.workers.tasks import scrape_zone_retail


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
    assert "New merchant emails (new contacts): 9" in body
    assert "Net new merchant emails" not in body
    assert "Category mix" in body
    assert "Restaurants" in body


class _Scalar:
    def scalar_one(self) -> int:
        return 7


class _RecordingConn:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: object, _params: object = None) -> _Scalar:
        self.statements.append(str(statement))
        return _Scalar()

    def __enter__(self) -> _RecordingConn:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


class _RecordingEngine:
    def __init__(self) -> None:
        self.conn = _RecordingConn()

    def connect(self) -> _RecordingConn:
        return self.conn


def test_merchant_email_count_is_new_contacts_only() -> None:
    engine = _RecordingEngine()
    counts = _query_window_counts(
        engine,  # type: ignore[arg-type]
        datetime(2026, 10, 8, 6, tzinfo=timezone.utc),
    )
    email_sql = [sql for sql in engine.conn.statements if "marketing_contacts" in sql]
    assert len(email_sql) == 1
    assert "created_at >= " in email_sql[0]
    assert "updated_at" not in email_sql[0]
    assert counts["new_email_rows"] == 7
    assert counts["net_new_emails"] == 7
    assert "gained_email_rows" not in counts


def test_crashed_and_running_zones_are_failed_not_ok() -> None:
    health = _zone_health(
        {
            "se_asia": {
                "ok": False,
                "status": "failed",
                "error": "Invalid IPv6 URL",
            },
            "us_east": {"ok": False, "status": "running"},
            "australia": {"ok": True, "status": "completed"},
        }
    )
    assert set(health["failed"]) == {"se_asia", "us_east"}
    assert health["interrupted"] == []
    assert "australia" not in health["failed"]
    assert health["ok"] == 1
    assert health["completed"] == 2
    assert "us_east" not in health["missing"]


def test_digest_does_not_mark_db_activity_as_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest.load_cycle_zone_results",
        lambda _cycle_id: {
            "se_asia": {"ok": False, "status": "failed", "error": "Invalid IPv6 URL"},
        },
    )
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest.load_cycle_zone_set",
        lambda _cycle_id: None,
    )
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest._alive_worker_hostnames",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest._query_window_counts",
        lambda _engine, _since: {
            "new_deals": 3,
            "dropped_deals": 0,
            "net_new_emails": 1,
            "new_email_rows": 1,
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
    assert "se_asia" in report["zones"]["failed"]
    assert report["zones"]["ok"] == 0
    assert "us_east" in report["zones"]["missing"]
    assert "se_asia" not in report["zones"]["missing"]
    body = format_digest_body(report)
    assert "Failed: se_asia" in body
    assert "100% ok" not in body


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def scan_iter(self, match: str | None = None):
        for key in list(self.values):
            if match is None or fnmatch.fnmatch(key, match):
                yield key


def _digest_body(zones: dict) -> str:
    return format_digest_body(
        {
            "cycle_id": "2026-10-08T06",
            "since_label": "2026-10-08 06:00",
            "zones": zones,
            "site": {
                "healthy": True,
                "api_ok": True,
                "frontend_ok": True,
                "revalidate_ok": 1,
                "revalidate_fail": 0,
                "revalidate_pct": 100.0,
                "detail": "ok",
            },
            "new_deals": 0,
            "dropped_deals": 0,
            "net_new_emails": 0,
            "categories": [],
        }
    )


def test_overdue_running_zone_is_interrupted_in_the_digest() -> None:
    now = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)
    started = (now - timedelta(hours=12)).isoformat()
    health = _zone_health(
        {
            "us_east": {
                "ok": False,
                "status": "running",
                "recorded_at": started,
                "worker_hostname": "scrape@nuc",
            },
            "australia": {"ok": True, "status": "completed"},
        },
        now=now,
        alive_workers={"scrape@nuc", "maintenance@nuc"},
    )
    assert health["interrupted"] == ["us_east"]
    assert "us_east" not in health["failed"]
    assert "us_east" not in health["missing"]
    assert health["ok"] == 1
    body = _digest_body(health)
    assert "Interrupted: us_east" in body
    assert "Failed:" not in body
    missing = next(line for line in body.splitlines() if line.startswith("Missing:"))
    assert "us_east" not in missing
    assert body.startswith("Cycle 2026-10-08T06")
    assert "Zones:" in body.splitlines()[1]


def test_running_zone_inside_the_time_limit_stays_failed() -> None:
    now = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)
    health = _zone_health(
        {
            "se_asia": {
                "ok": False,
                "status": "running",
                "recorded_at": (now - timedelta(seconds=ZONE_TASK_TIME_LIMIT_SECONDS)).isoformat(),
                "worker_hostname": "scrape@nuc",
            }
        },
        now=now,
        alive_workers={"scrape@nuc"},
    )
    assert health["interrupted"] == []
    assert "se_asia" in health["failed"]


def test_running_zone_past_the_grace_is_interrupted() -> None:
    now = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)
    elapsed = ZONE_TASK_TIME_LIMIT_SECONDS + _RUNNING_GRACE_SECONDS + 1
    health = _zone_health(
        {
            "se_asia": {
                "ok": False,
                "status": "running",
                "recorded_at": (now - timedelta(seconds=elapsed)).isoformat(),
                "worker_hostname": "scrape@nuc",
            }
        },
        now=now,
        alive_workers={"scrape@nuc"},
    )
    assert health["interrupted"] == ["se_asia"]
    assert "se_asia" not in health["failed"]
    assert "se_asia" not in health["missing"]


def test_running_zone_whose_worker_is_gone_is_interrupted() -> None:
    now = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    health = _zone_health(
        {
            "se_asia": {
                "ok": False,
                "status": "running",
                "recorded_at": datetime(2026, 10, 8, 11, 30, tzinfo=timezone.utc).isoformat(),
                "worker_hostname": "scrape@nuc",
            }
        },
        now=now,
        alive_workers={"maintenance@nuc"},
    )
    assert health["interrupted"] == ["se_asia"]
    assert "se_asia" not in health["failed"]
    assert "se_asia" not in health["missing"]
    body = _digest_body(health)
    assert "Interrupted: se_asia" in body


def test_foreign_recorded_zones_are_not_missing_current_zones() -> None:
    health = _zone_health(
        {
            "us": {"ok": True, "status": "completed"},
            "west_eu_core": {"ok": False, "status": "failed", "error": "boom"},
            "se_asia": {"ok": True, "status": "completed"},
        }
    )
    assert health["missing"] == []
    assert health["total_zones"] == 3
    assert health["completed"] == 3
    assert health["ok"] == 2
    assert "west_eu_core" in health["failed"]
    assert health["large_families"] == []
    assert health["zone_set_note"]
    body = _digest_body(health)
    assert "Zone set:" in body
    assert "us" in body
    assert "west_eu_core" in body
    assert "Missing:" not in body
    assert "Large ·" not in body
    assert "us_east" not in body


def test_scheduled_zone_set_is_what_the_digest_scores() -> None:
    now = datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc)
    health = _zone_health(
        {
            "eastern_europe": {"ok": True, "status": "completed"},
            "us": {
                "ok": False,
                "status": "running",
                "recorded_at": "2026-10-08T06:00:00+00:00",
            },
        },
        now=now,
        scheduled_zones=["eastern_europe", "us", "west_eu_core"],
    )
    assert health["missing"] == ["west_eu_core"]
    assert health["interrupted"] == ["us"]
    assert health["total_zones"] == 3
    assert "us_east" not in health["missing"]
    assert "different zone set" in (health["zone_set_note"] or "")
    body = _digest_body(health)
    assert "Missing: west_eu_core" in body
    assert "Interrupted: us" in body
    assert "us_east" not in body
    assert "Zone set:" in body
    assert body.splitlines()[1].startswith("Zones:")


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


def test_load_cycle_results_includes_retired_zone_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    record_zone_result(
        "us",
        {"ok": True, "status": "completed"},
        cycle_id="2026-10-08T06",
    )
    record_zone_result(
        "se_asia",
        {"ok": True, "status": "completed"},
        cycle_id="2026-10-08T06",
    )
    remember_cycle_zone_set("2026-10-08T06", ["us", "west_eu_core"])
    loaded = load_cycle_zone_results("2026-10-08T06")
    assert set(loaded) == {"us", "se_asia"}
    assert load_cycle_zone_set("2026-10-08T06") == ["us", "west_eu_core"]


def test_zone_set_keeps_the_first_publisher(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    remember_cycle_zone_set("2026-10-08T06", ["us", "west_eu_core"])
    remember_cycle_zone_set("2026-10-08T06", list(ZONE_ORDER))
    assert load_cycle_zone_set("2026-10-08T06") == ["us", "west_eu_core"]


def test_publish_stamp_remembers_the_zone_set(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def _remember(cycle_id: str, zones: list[str]) -> None:
        seen["cycle_id"] = cycle_id
        seen["zones"] = list(zones)

    monkeypatch.setattr("app.workers.celery_app.remember_cycle_zone_set", _remember)
    headers: dict[str, str] = {}
    _stamp_scrape_cycle_id(
        sender="app.workers.tasks.scrape_zone_retail",
        headers=headers,
    )
    assert headers["scrape_cycle_id"] == seen["cycle_id"]
    assert seen["zones"] == list(ZONE_ORDER)

    headers = {"scrape_cycle_id": "2026-10-08T06"}
    _stamp_scrape_cycle_id(
        sender="app.workers.tasks.scrape_zone_retail",
        headers=headers,
    )
    assert headers["scrape_cycle_id"] == "2026-10-08T06"
    assert seen["cycle_id"] == "2026-10-08T06"


@pytest.mark.parametrize("raw_zone", ["us", "west_eu_core", "US"])
def test_unknown_scrape_zone_is_skipped(
    raw_zone: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unknown zone must not scrape or record")

    monkeypatch.setattr("app.workers.tasks.record_zone_result", _boom)
    monkeypatch.setattr("app.workers.tasks.scrape_and_ingest_zone", _boom)
    monkeypatch.setattr("app.workers.tasks.zone_already_succeeded", _boom)

    with caplog.at_level(logging.WARNING, logger="app.workers.tasks"):
        result = scrape_zone_retail.run(raw_zone)

    assert result["ok"] is True
    assert result["status"] == "skipped"
    assert result["skipped"] == "unknown_zone"
    assert result["zone"] == raw_zone.strip().lower()
    assert "Unknown scrape zone" in caplog.text
    assert raw_zone in caplog.text


def test_running_marker_records_worker_hostname(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[dict[str, object]] = []

    def _record(zone: str, payload: dict[str, object], cycle_id: str | None = None) -> str:
        recorded.append(payload)
        return cycle_id or ""

    monkeypatch.setattr("app.workers.tasks.zone_already_succeeded", lambda *_a, **_k: False)
    monkeypatch.setattr("app.workers.tasks.record_zone_result", _record)
    monkeypatch.setattr(
        "app.workers.tasks.scrape_and_ingest_zone",
        lambda _zone: {
            "areas": 1,
            "discovered": 1,
            "ingested": 1,
            "stale_deactivated": 0,
            "marketing_contacts": 0,
            "revalidate_ok": 0,
            "revalidate_fail": 0,
            "cities_failed": [],
        },
    )

    scrape_zone_retail.push_request(hostname="scrape@nuc")
    try:
        result = scrape_zone_retail.run("se_asia")
    finally:
        scrape_zone_retail.pop_request()

    assert recorded[0]["status"] == "running"
    assert recorded[0]["worker_hostname"] == "scrape@nuc"
    assert result["status"] == "completed"
