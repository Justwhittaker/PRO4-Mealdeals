"""Unit tests for scrape cycle digest formatting / cycle windows."""

from __future__ import annotations

import fnmatch
import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.scrapers.zones import ZONE_ORDER, ZONE_TASK_TIME_LIMIT_SECONDS
from app.services.scrape_cycle_digest import (
    _RUNNING_GRACE_SECONDS,
    _active_offers_on_site,
    _cycle_duration_line,
    _digest_priority,
    _query_window_counts,
    _site_transfer_health,
    _zone_health,
    build_cycle_digest_report,
    format_city_retry_line,
    format_digest_body,
    pending_city_retry_labels,
    publish_cycle_digest,
    queue_failed_city_retries,
    run_city_retry,
)
from app.services.scrape_cycle_stats import (
    claim_city_retries,
    cycle_id_for_start,
    cycle_id_from_task_request,
    cycle_start_for_time,
    digest_cycle_start,
    load_city_retries,
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
            "active_offers": 2464,
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
    assert "Active offers on site: 2464" in body
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
    site_sql = [
        sql
        for sql in engine.conn.statements
        if "FROM deals" in sql and "is_active IS TRUE" in sql and "scraped_raw_url" not in sql
    ]
    assert len(site_sql) == 1


def test_active_offers_uses_site_metrics_then_the_database() -> None:
    assert _active_offers_on_site(2464, 1800) == 2464
    assert _active_offers_on_site(0, 1800) == 0
    assert _active_offers_on_site(None, 1800) == 1800


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
    assert health["failed"] == ["se_asia"]
    assert health["still_running"] == ["us_east"]
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
        "app.services.scrape_cycle_digest.load_city_retries",
        lambda _cycle_id: [],
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
            "active_site_deals": 18,
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
    assert report["active_offers"] == 18
    body = format_digest_body(report)
    assert "Failed: se_asia" in body
    assert "Active offers on site: 18" in body
    assert "100% ok" not in body


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.values[key] = value

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def expire(self, _key: str, _ttl: int) -> bool:
        return True

    def hsetnx(self, key: str, field: str, value: str) -> int:
        bucket = self.hashes.setdefault(key, {})
        if field in bucket:
            return 0
        bucket[field] = value
        return 1

    def hset(self, key: str, field: str, value: str) -> int:
        bucket = self.hashes.setdefault(key, {})
        bucket[field] = value
        return 1

    def hget(self, key: str, field: str) -> str | None:
        return self.hashes.get(key, {}).get(field)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def scan_iter(self, match: str | None = None):
        for key in list(self.values):
            if match is None or fnmatch.fnmatch(key, match):
                yield key


def _digest_body(
    zones: dict,
    *,
    cycle_results: dict | None = None,
    since: str | None = None,
    city_retries: list | None = None,
) -> str:
    report: dict = {
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
        "active_offers": 0,
        "categories": [],
    }
    if cycle_results is not None:
        report["cycle_results"] = cycle_results
    if since is not None:
        report["since"] = since
    if city_retries is not None:
        report["city_retries"] = city_retries
    return format_digest_body(report)


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


def test_running_zone_inside_the_time_limit_is_still_running() -> None:
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
    assert health["still_running"] == ["se_asia"]
    assert "se_asia" not in health["failed"]
    assert "Still running: se_asia" in _digest_body(health)


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
    started_at = recorded[0]["started_at"]
    assert isinstance(started_at, str)
    assert started_at.endswith("+00:00")
    assert recorded[-1]["started_at"] == started_at
    assert result["started_at"] == started_at


def test_failure_payload_keeps_the_zone_started_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, object]] = []

    def _record(zone: str, payload: dict[str, object], cycle_id: str | None = None) -> str:
        recorded.append(payload)
        return cycle_id or ""

    def _boom(_zone: str) -> dict[str, object]:
        raise RuntimeError("Invalid IPv6 URL")

    monkeypatch.setattr("app.workers.tasks.zone_already_succeeded", lambda *_a, **_k: False)
    monkeypatch.setattr("app.workers.tasks.record_zone_result", _record)
    monkeypatch.setattr("app.workers.tasks.scrape_and_ingest_zone", _boom)

    with pytest.raises(RuntimeError, match="Invalid IPv6 URL"):
        scrape_zone_retail.run("se_asia")

    assert recorded[0]["status"] == "running"
    assert recorded[1]["status"] == "failed"
    assert recorded[0]["started_at"] == recorded[1]["started_at"]
    assert str(recorded[0]["started_at"]).endswith("+00:00")


def test_cycle_duration_line_uses_earliest_start_and_latest_finish() -> None:
    line = _cycle_duration_line(
        {
            "australia": {
                "status": "completed",
                "started_at": "2026-10-08T18:00:00+00:00",
                "recorded_at": "2026-10-08T21:00:00+00:00",
            },
            "se_asia": {
                "status": "completed",
                "started_at": "2026-10-08T19:00:00+00:00",
                "recorded_at": "2026-10-08T22:18:00+00:00",
            },
        },
        since="2026-10-08T17:00:00+00:00",
    )
    assert line == "Duration: 4h 18m (19:00–23:18 Dublin)"


def test_cycle_duration_line_falls_back_to_cycle_start() -> None:
    line = _cycle_duration_line(
        {
            "se_asia": {
                "status": "completed",
                "recorded_at": "2026-10-08T22:18:00+00:00",
            },
        },
        since=datetime(2026, 10, 8, 18, 0, tzinfo=timezone.utc),
    )
    assert line == "Duration: 4h 18m (~19:00–23:18 Dublin)"


def test_cycle_duration_line_ignores_running_zones_when_picking_the_finish() -> None:
    line = _cycle_duration_line(
        {
            "australia": {
                "status": "completed",
                "started_at": "2026-10-08T18:30:00+00:00",
                "recorded_at": "2026-10-08T21:00:00+00:00",
            },
            "se_asia": {
                "status": "running",
                "started_at": "2026-10-08T18:00:00+00:00",
                "recorded_at": "2026-10-08T23:30:00+00:00",
            },
        },
        since="2026-10-08T18:00:00+00:00",
    )
    assert line == "Duration: 3h 0m (19:00–22:00 Dublin)"
    assert (
        _cycle_duration_line(
            {
                "se_asia": {
                    "status": "running",
                    "started_at": "2026-10-08T18:00:00+00:00",
                    "recorded_at": "2026-10-08T23:30:00+00:00",
                },
            },
            since="2026-10-08T18:00:00+00:00",
        )
        is None
    )


def test_cycle_duration_line_without_results() -> None:
    assert _cycle_duration_line({}, since="2026-10-08T18:00:00+00:00") is None
    assert (
        _cycle_duration_line(
            {"se_asia": {"status": "completed", "ok": True}},
            since="2026-10-08T18:00:00+00:00",
        )
        is None
    )


def test_cycle_duration_line_spans_midnight() -> None:
    line = _cycle_duration_line(
        {
            "us_east": {
                "status": "timed_out",
                "started_at": "2026-10-08T22:30:00+00:00",
                "recorded_at": "2026-10-09T01:15:00+00:00",
            },
        },
        since="2026-10-08T18:00:00+00:00",
    )
    assert line == "Duration: 2h 45m (23:30–02:15 Dublin)"


def test_format_digest_body_puts_duration_after_the_cycle_line() -> None:
    zones = {
        "total_zones": 1,
        "completed": 1,
        "ok": 1,
        "failed": [],
        "missing": [],
        "pct_completed": 100.0,
        "pct_ok": 100.0,
    }
    body = _digest_body(
        zones,
        cycle_results={
            "australia": {
                "status": "completed",
                "started_at": "2026-10-08T18:00:00+00:00",
                "recorded_at": "2026-10-08T22:18:00+00:00",
            },
        },
        since="2026-10-08T18:00:00+00:00",
    )
    lines = body.splitlines()
    assert lines[0] == "Cycle 2026-10-08T06 (since 2026-10-08 06:00 UTC)"
    assert lines[1] == "Duration: 4h 18m (19:00–23:18 Dublin)"
    assert lines[2].startswith("Zones:")

    open_cycle = _digest_body(
        zones,
        cycle_results={
            "se_asia": {
                "status": "running",
                "started_at": "2026-10-08T18:00:00+00:00",
                "recorded_at": "2026-10-08T22:18:00+00:00",
            },
        },
        since="2026-10-08T18:00:00+00:00",
    )
    assert "Duration:" not in open_cycle
    assert open_cycle.splitlines()[1].startswith("Zones:")


_RECONNECT = "Can't reconnect until invalid transaction is rolled back"


def _cycle_with_failed_cities() -> dict:
    return {
        "us_east": {
            "status": "completed",
            "cities_failed": [
                {"country": "US", "city": "Tampa", "error": _RECONNECT},
                {"country": "US", "city": "Seattle", "error": _RECONNECT},
            ],
        },
        "france_benelux": {
            "status": "failed",
            "cities_failed": [
                {
                    "country": "FR",
                    "city": "Bordeaux Wine Country",
                    "error": _RECONNECT,
                },
            ],
        },
        "us_west": {
            "status": "running",
            "cities_failed": [
                {"country": "US", "city": "Phoenix", "error": "still running"},
            ],
        },
    }


def test_each_failed_city_is_claimed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    cities = [("US", "Tampa"), ("US", "Seattle"), ("FR", "Bordeaux Wine Country")]
    assert claim_city_retries("2026-10-08T18", cities) == cities
    assert claim_city_retries("2026-10-08T18", cities) == []


def test_duplicate_digest_trigger_does_not_requeue_city_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    calls: list[tuple[str, str, str]] = []

    def _enqueue(cycle_id: str, country: str, city: str) -> None:
        calls.append((cycle_id, country, city))

    results = _cycle_with_failed_cities()
    first = queue_failed_city_retries("2026-10-08T18", results, enqueue=_enqueue)
    second = queue_failed_city_retries("2026-10-08T18", results, enqueue=_enqueue)
    assert first == [
        ("US", "Tampa"),
        ("US", "Seattle"),
        ("FR", "Bordeaux Wine Country"),
    ]
    assert ("US", "Phoenix") not in first
    assert second == []
    assert calls == [
        ("2026-10-08T18", "US", "Tampa"),
        ("2026-10-08T18", "US", "Seattle"),
        ("2026-10-08T18", "FR", "Bordeaux Wine Country"),
    ]


def test_city_retry_runs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest.send_ntfy",
        lambda *_args, **_kwargs: {"ok": True},
    )
    claim_city_retries("2026-10-08T18", [("US", "Tampa")])
    calls: list[tuple[str, str]] = []

    def _scrape(country: str, city: str) -> dict[str, int]:
        calls.append((country, city))
        return {"ingested": 1}

    first = run_city_retry("2026-10-08T18", "US", "Tampa", scrape=_scrape)
    second = run_city_retry("2026-10-08T18", "US", "Tampa", scrape=_scrape)
    assert calls == [("US", "Tampa")]
    assert first["ok"] is True
    assert second["skipped"] is True
    assert load_city_retries("2026-10-08T18")[0]["status"] == "recovered"


def test_a_failed_city_retry_is_not_run_again(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest.send_ntfy",
        lambda *_args, **_kwargs: {"ok": True},
    )
    claim_city_retries("2026-10-08T18", [("US", "Tampa")])
    calls: list[str] = []

    def _scrape(_country: str, city: str) -> dict[str, int]:
        calls.append(city)
        raise RuntimeError("Can't reconnect until invalid transaction is rolled back")

    first = run_city_retry("2026-10-08T18", "US", "Tampa", scrape=_scrape)
    second = run_city_retry("2026-10-08T18", "US", "Tampa", scrape=_scrape)
    assert calls == ["Tampa"]
    assert first["ok"] is False
    assert second["skipped"] is True
    assert load_city_retries("2026-10-08T18")[0]["status"] == "failed"


def test_format_digest_body_includes_city_retry_line() -> None:
    zones = {
        "total_zones": 2,
        "completed": 2,
        "ok": 1,
        "failed": ["france_benelux"],
        "missing": [],
        "pct_completed": 100.0,
        "pct_ok": 50.0,
    }
    retries = [
        {"status": "recovered", "country": "US", "city": "Seattle"},
        {"status": "failed", "country": "US", "city": "Tampa"},
        {"status": "failed", "country": "FR", "city": "Bordeaux Wine Country"},
    ]
    line = format_city_retry_line(retries)
    assert line == (
        "City retries: 1 recovered, 2 still failing: "
        "Bordeaux Wine Country (FR), Tampa (US)"
    )
    body = _digest_body(zones, city_retries=retries)
    zone_at = body.index("Zones:")
    retry_at = body.index(line or "")
    site_at = body.index("Site transfer:")
    assert zone_at < retry_at < site_at

    pending = _digest_body(
        zones,
        city_retries=[
            {"status": "queued", "country": "US", "city": "Tampa"},
            {"status": "recovered", "country": "US", "city": "Seattle"},
        ],
    )
    assert "City retries:" not in pending
    assert format_city_retry_line([]) is None
    assert format_city_retry_line(None) is None


def _sample_digest_report() -> dict:
    return {
        "cycle_id": "2026-10-08T18",
        "since_label": "2026-10-08 18:00",
        "zones": {
            "total_zones": 2,
            "completed": 1,
            "ok": 1,
            "failed": [],
            "missing": [],
            "interrupted": [],
            "still_running": ["us_east", "se_asia"],
            "pct_completed": 50.0,
            "pct_ok": 50.0,
        },
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
        "active_offers": 0,
        "categories": [],
        "city_retries": [
            {"status": "running", "country": "US", "city": "Tampa"},
            {"status": "queued", "country": "FR", "city": "Bordeaux Wine Country"},
            {"status": "recovered", "country": "US", "city": "Seattle"},
        ],
    }


def test_digest_names_zones_and_retries_still_running() -> None:
    report = _sample_digest_report()
    body = format_digest_body(report)
    assert (
        "Still running: us_east, se_asia, "
        "Bordeaux Wine Country (FR), Tampa (US)"
    ) in body
    assert "City retries:" not in body
    assert pending_city_retry_labels(report["city_retries"]) == [
        "Bordeaux Wine Country (FR)",
        "Tampa (US)",
    ]


def test_digest_is_sent_once_per_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    sent: list[str] = []

    def _send(_title: str, body: str, **_kwargs: object) -> dict[str, bool]:
        sent.append(body)
        return {"ok": True}

    monkeypatch.setattr("app.services.scrape_cycle_digest.send_ntfy", _send)
    report = _sample_digest_report()
    first = publish_cycle_digest(report)
    second = publish_cycle_digest(report)
    assert first["ntfy"] == {"ok": True}
    assert second["ntfy"] == {"skipped": True, "reason": "already_sent"}
    assert len(sent) == 1
    assert "Still running: us_east, se_asia" in sent[0]


def test_digest_cycle_matches_across_the_october_dst_change() -> None:
    dublin = ZoneInfo("Europe/Dublin")

    summer_publish = datetime(2026, 10, 8, 19, 5, tzinfo=dublin)
    summer_id = cycle_id_for_start(cycle_start_for_time(summer_publish))
    summer_digest = datetime(2026, 10, 9, 6, 0, tzinfo=dublin)
    assert summer_digest.utcoffset() == timedelta(hours=1)
    assert cycle_id_for_start(digest_cycle_start(summer_digest)) == summer_id
    assert summer_id == "2026-10-08T18"

    # 25 Oct 2026 01:00 UTC: Ireland falls back from IST (UTC+1) to GMT.
    evening_before = datetime(2026, 10, 24, 19, 5, tzinfo=dublin)
    assert evening_before.utcoffset() == timedelta(hours=1)
    folded_id = cycle_id_for_start(cycle_start_for_time(evening_before))
    morning_after = datetime(2026, 10, 25, 6, 0, tzinfo=dublin)
    assert morning_after.utcoffset() == timedelta(0)
    assert cycle_id_for_start(digest_cycle_start(morning_after)) == folded_id
    assert folded_id == "2026-10-24T18"

    morning_publish = datetime(2026, 10, 25, 7, 10, tzinfo=dublin)
    assert morning_publish.utcoffset() == timedelta(0)
    winter_morning_id = cycle_id_for_start(cycle_start_for_time(morning_publish))
    same_day_digest = datetime(2026, 10, 25, 18, 0, tzinfo=dublin)
    assert cycle_id_for_start(digest_cycle_start(same_day_digest)) == winter_morning_id
    assert winter_morning_id == "2026-10-25T07"

    winter_publish = datetime(2026, 10, 26, 19, 0, tzinfo=dublin)
    winter_id = cycle_id_for_start(cycle_start_for_time(winter_publish))
    winter_digest = datetime(2026, 10, 27, 6, 5, tzinfo=dublin)
    assert winter_digest.utcoffset() == timedelta(0)
    assert cycle_id_for_start(digest_cycle_start(winter_digest)) == winter_id
    assert winter_id == "2026-10-26T19"


_CHECKPOINT_HTML = (
    "<!DOCTYPE html><html><head><title>Vercel Security Checkpoint</title></head>"
    "<body>" + ("checkpoint " * 400) + "</body></html>"
)
_PROBE_SETTINGS = SimpleNamespace(
    public_api_base_url="https://api.example",
    frontend_base_url="https://dineadeal.com",
)


def _metrics_response(active: int = 100) -> httpx.Response:
    return httpx.Response(200, json={"active_deals": active})


def _challenge_response(*, header: bool = True, title: bool = True) -> httpx.Response:
    headers = {"x-vercel-mitigated": "Challenge"} if header else {}
    text = _CHECKPOINT_HTML if title else "attention required"
    return httpx.Response(429, headers=headers, text=text)


def _install_site_probe(
    monkeypatch: pytest.MonkeyPatch,
    *,
    api: httpx.Response | Exception,
    web: httpx.Response | Exception,
) -> None:
    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            return None

        def __enter__(self) -> _Client:
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def get(self, url: str) -> httpx.Response:
            outcome = api if url.endswith("/api/v1/scrapers/metrics") else web
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr("app.services.scrape_cycle_digest.httpx.Client", _Client)
    monkeypatch.setattr(
        "app.services.scrape_cycle_digest.get_settings",
        lambda: _PROBE_SETTINGS,
    )


def _complete_zones() -> dict:
    return {
        "total_zones": 2,
        "completed": 2,
        "ok": 2,
        "failed": [],
        "missing": [],
        "pct_completed": 100.0,
        "pct_ok": 100.0,
    }


def _report_with_site(site: dict, *, pct_completed: float = 100.0) -> dict:
    zones = _complete_zones()
    zones["pct_completed"] = pct_completed
    zones["completed"] = 2 if pct_completed == 100.0 else 1
    return {
        "cycle_id": "2026-11-09T07",
        "since_label": "2026-11-09 07:00",
        "zones": zones,
        "site": site,
        "new_deals": 0,
        "dropped_deals": 0,
        "net_new_emails": 0,
        "active_offers": 100,
        "categories": [],
    }


def test_vercel_challenge_429_counts_as_the_site_being_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_site_probe(
        monkeypatch,
        api=_metrics_response(),
        web=_challenge_response(),
    )
    health = _site_transfer_health(
        cycle_results={
            "west_eu": {"revalidate_challenge": 300},
            "se_asia": {"revalidate_challenge": 221},
        },
        db_active=100,
    )
    assert health["api_ok"] is True
    assert health["frontend_ok"] is True
    assert health["frontend_challenge"] is True
    assert health["healthy"] is True
    assert health["revalidate_ok"] == 0
    assert health["revalidate_fail"] == 0
    assert health["revalidate_challenge"] == 521
    assert health["revalidate_pct"] is None
    assert health["detail"] == "ok"
    assert "429" not in health["detail"]


def test_checkpoint_title_alone_counts_as_up(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_site_probe(
        monkeypatch,
        api=_metrics_response(),
        web=_challenge_response(header=False, title=True),
    )
    health = _site_transfer_health(cycle_results={}, db_active=100)
    assert health["frontend_ok"] is True
    assert health["frontend_challenge"] is True
    assert health["healthy"] is True


def test_plain_429_without_checkpoint_markers_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_site_probe(
        monkeypatch,
        api=_metrics_response(),
        web=httpx.Response(429, text="Too Many Requests"),
    )
    health = _site_transfer_health(cycle_results={}, db_active=100)
    assert health["frontend_ok"] is False
    assert health["frontend_challenge"] is False
    assert health["healthy"] is False
    assert health["detail"] == "site HTTP 429"


@pytest.mark.parametrize(
    "web",
    [
        httpx.Response(500, text="<html><title>Bad gateway</title></html>"),
        httpx.Response(
            403,
            headers={"x-vercel-mitigated": "challenge"},
            text=_CHECKPOINT_HTML,
        ),
        httpx.Response(401, text="Unauthorized"),
        httpx.ConnectError("connection refused"),
        httpx.TimeoutException("timed out"),
    ],
)
def test_real_site_failures_stay_down(
    web: httpx.Response | Exception,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_site_probe(monkeypatch, api=_metrics_response(), web=web)
    health = _site_transfer_health(cycle_results={}, db_active=100)
    assert health["frontend_ok"] is False
    assert health["frontend_challenge"] is False
    assert health["healthy"] is False
    assert health["api_ok"] is True
    body = format_digest_body(_report_with_site(health))
    assert "web=down" in body
    assert "Vercel bot check" not in body
    priority, tags = _digest_priority(_report_with_site(health))
    assert priority == "high"
    assert tags == "warning,newspaper"


def test_api_and_web_both_down_stays_urgent(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_site_probe(
        monkeypatch,
        api=httpx.ConnectError("api down"),
        web=httpx.Response(503, text="unavailable"),
    )
    health = _site_transfer_health(cycle_results={}, db_active=100)
    assert health["api_ok"] is False
    assert health["frontend_ok"] is False
    report = _report_with_site(health)
    priority, tags = _digest_priority(report)
    assert priority == "urgent"
    assert tags == "rotating_light,newspaper"
    body = format_digest_body(report)
    assert "api=down" in body
    assert "web=down" in body
    assert "site HTTP 503" in body


def test_november_9_challenge_digest_is_not_a_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """18:00 Dublin on 9 Nov 2026: every revalidate and the homepage were challenged."""
    _install_site_probe(
        monkeypatch,
        api=_metrics_response(2464),
        web=_challenge_response(),
    )
    health = _site_transfer_health(
        cycle_results={
            "west_eu": {"revalidate_ok": 0, "revalidate_fail": 0, "revalidate_challenge": 521},
        },
        db_active=2464,
    )
    report = _report_with_site(health)
    body = format_digest_body(report)
    assert (
        "Site transfer: OK — Page refresh blocked by Vercel bot check (521 calls); "
        "pages update on their normal cache timer"
    ) in body
    assert "Live: api=up, web=up (Vercel bot check)" in body
    assert "CHECK" not in body
    assert "revalidate 0%" not in body
    assert "web=down" not in body
    assert "site HTTP 429" not in body
    assert "redis://" not in body
    priority, tags = _digest_priority(report)
    assert priority == "default"
    assert tags == "newspaper"

    fake = _FakeRedis()
    monkeypatch.setattr("app.services.scrape_cycle_stats._client", lambda: fake)
    sent: list[dict[str, object]] = []

    def _send(
        _title: str,
        message: str,
        *,
        priority: str = "default",
        tags: str | None = None,
    ) -> dict[str, bool]:
        sent.append({"body": message, "priority": priority, "tags": tags})
        return {"ok": True}

    monkeypatch.setattr("app.services.scrape_cycle_digest.send_ntfy", _send)
    published = publish_cycle_digest(report)
    assert published["ntfy"] == {"ok": True}
    assert sent[0]["priority"] == "default"
    assert sent[0]["tags"] == "newspaper"
    assert sent[0]["body"] == body


def test_challenge_revalidates_mixed_with_real_failures_still_warn() -> None:
    site = {
        "healthy": False,
        "api_ok": True,
        "frontend_ok": True,
        "frontend_challenge": True,
        "revalidate_ok": 0,
        "revalidate_fail": 4,
        "revalidate_challenge": 521,
        "revalidate_pct": 0.0,
        "detail": "ok",
    }
    report = _report_with_site(site)
    body = format_digest_body(report)
    assert "Site transfer: CHECK — revalidate 0% (0 ok / 4 fail)" in body
    assert (
        "Page refresh blocked by Vercel bot check (521 calls); "
        "pages update on their normal cache timer"
    ) in body
    assert "web=up (Vercel bot check)" in body
    assert "web=down" not in body
    priority, tags = _digest_priority(report)
    assert priority == "high"
    assert tags == "warning,newspaper"


def test_mostly_successful_revalidate_stays_quiet_with_a_few_challenges() -> None:
    site = {
        "healthy": True,
        "api_ok": True,
        "frontend_ok": True,
        "frontend_challenge": False,
        "revalidate_ok": 95,
        "revalidate_fail": 5,
        "revalidate_challenge": 1,
        "revalidate_pct": 95.0,
        "detail": "ok",
    }
    report = _report_with_site(site)
    body = format_digest_body(report)
    assert "Site transfer: OK — revalidate 95% (95 ok / 5 fail)" in body
    assert (
        "Page refresh blocked by Vercel bot check (1 call); "
        "pages update on their normal cache timer"
    ) in body
    priority, tags = _digest_priority(report)
    assert priority == "default"
    assert tags == "newspaper"


def test_auth_and_server_revalidate_failures_keep_the_warning() -> None:
    site = {
        "healthy": False,
        "api_ok": True,
        "frontend_ok": True,
        "frontend_challenge": False,
        "revalidate_ok": 0,
        "revalidate_fail": 3,
        "revalidate_challenge": 0,
        "revalidate_pct": 0.0,
        "detail": "ok",
    }
    report = _report_with_site(site)
    body = format_digest_body(report)
    assert "Site transfer: CHECK — revalidate 0% (0 ok / 3 fail)" in body
    assert "Page refresh blocked" not in body
    assert "web=up" in body
    priority, tags = _digest_priority(report)
    assert priority == "high"
    assert tags == "warning,newspaper"


def test_incomplete_zones_still_escalate_when_the_site_is_only_challenged() -> None:
    site = {
        "healthy": True,
        "api_ok": True,
        "frontend_ok": True,
        "frontend_challenge": True,
        "revalidate_ok": 0,
        "revalidate_fail": 0,
        "revalidate_challenge": 521,
        "revalidate_pct": None,
        "detail": "ok",
    }
    high = _report_with_site(site, pct_completed=80.0)
    priority, tags = _digest_priority(high)
    assert priority == "high"
    assert tags == "warning,newspaper"
    urgent = _report_with_site(site, pct_completed=40.0)
    priority, tags = _digest_priority(urgent)
    assert priority == "urgent"
    assert tags == "rotating_light,newspaper"


def test_active_count_mismatch_still_warns_when_the_homepage_is_challenged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_site_probe(
        monkeypatch,
        api=_metrics_response(10_000),
        web=_challenge_response(header=True, title=False),
    )
    health = _site_transfer_health(
        cycle_results={"west_eu": {"revalidate_challenge": 10}},
        db_active=100,
    )
    assert health["frontend_challenge"] is True
    assert health["healthy"] is False
    assert "active delta" in health["detail"]
    report = _report_with_site(health)
    priority, _tags = _digest_priority(report)
    assert priority == "high"
    body = format_digest_body(report)
    assert "web=up (Vercel bot check)" in body
    assert "CHECK" in body


def test_zone_summary_keeps_challenge_revalidates_apart_from_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[dict[str, object]] = []

    def _record(zone: str, payload: dict[str, object], cycle_id: str | None = None) -> str:
        recorded.append(payload)
        return cycle_id or ""

    monkeypatch.setattr("app.workers.tasks.zone_already_succeeded", lambda *_a, **_k: False)
    monkeypatch.setattr("app.workers.tasks.record_zone_result", _record)
    monkeypatch.setattr(
        "app.workers.tasks.scrape_and_ingest_zone",
        lambda _zone: {
            "areas": 3,
            "discovered": 3,
            "ingested": 3,
            "stale_deactivated": 0,
            "marketing_contacts": 0,
            "revalidate_ok": 1,
            "revalidate_fail": 2,
            "revalidate_challenge": 521,
            "cities_failed": [],
        },
    )

    result = scrape_zone_retail.run("se_asia")

    assert result["revalidate_ok"] == 1
    assert result["revalidate_fail"] == 2
    assert result["revalidate_challenge"] == 521
    assert recorded[-1]["revalidate_challenge"] == 521
    assert recorded[-1]["revalidate_fail"] == 2
