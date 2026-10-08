"""Six scrape workers share one Overpass budget and per-host gaps."""

from __future__ import annotations

import app.scrapers.politeness as politeness


def _isolated(monkeypatch) -> None:
    monkeypatch.setattr(politeness, "_redis_disabled", True)
    politeness._next_monotonic.clear()


def test_repeat_calls_to_one_host_wait(monkeypatch) -> None:
    _isolated(monkeypatch)
    assert politeness.reserve_slot("host:pizza.example", 0.5) == 0
    assert politeness.reserve_slot("host:pizza.example", 0.5) > 0.2
    assert politeness.reserve_slot("host:other.example", 0.5) == 0


def test_rate_limit_penalty_holds_the_host(monkeypatch) -> None:
    _isolated(monkeypatch)
    politeness.penalize("host:pizza.example", 30)
    assert politeness.reserve_slot("host:pizza.example", 0.5) > 20
    assert politeness.reserve_slot("overpass", 2) == 0


def test_overpass_gap_is_separate_from_hosts(monkeypatch) -> None:
    _isolated(monkeypatch)
    assert politeness.reserve_slot("overpass", politeness.OVERPASS_GAP_SECONDS) == 0
    wait = politeness.reserve_slot("overpass", politeness.OVERPASS_GAP_SECONDS)
    assert wait > 1
    assert politeness.OVERPASS_GAP_SECONDS >= 2
