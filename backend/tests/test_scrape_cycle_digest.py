"""Unit tests for scrape cycle digest formatting / cycle windows."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.scrape_cycle_digest import format_digest_body
from app.services.scrape_cycle_stats import cycle_start_for_time, digest_cycle_start


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
    assert "Site transfer: OK" in body
    assert "New deals: 12" in body
    assert "Dropped deals: 5" in body
    assert "Net new merchant emails: 9" in body
    assert "Category mix" in body
    assert "Restaurants" in body
