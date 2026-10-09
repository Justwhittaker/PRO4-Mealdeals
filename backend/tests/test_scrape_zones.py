"""Zone registry coverage / large-scrape split invariants."""

from __future__ import annotations

import pytest

from app.scrapers.zones import (
    LARGE_ZONE_FAMILIES,
    MAX_ZONE_AREAS,
    MAINTENANCE_QUEUE,
    REDIS_VISIBILITY_TIMEOUT_SECONDS,
    SCRAPE_QUEUE,
    SCRAPE_ZONES,
    ZONE_BEAT_SLOTS,
    ZONE_ORDER,
    ZONE_TASK_SOFT_TIME_LIMIT_SECONDS,
    ZONE_TASK_TIME_LIMIT_SECONDS,
    iter_zone_areas,
    markets_for_zone,
    scrape_concurrency,
    validate_zone_coverage,
    zone_family,
    zone_for_area,
    zone_for_country,
    zone_size_class,
)
from app.workers.celery_app import celery_app
from app.workers.tasks import scrape_zone_retail


def test_validate_zone_coverage() -> None:
    validate_zone_coverage()


def test_us_and_western_europe_are_large_family_splits() -> None:
    assert zone_for_country("CA") == "canada"
    assert zone_for_country("GB") == "british_isles"
    assert zone_for_country("FR") == "france_benelux"
    assert zone_for_country("ES") == "iberia"
    assert zone_for_area("US", "New York") == "us_east"
    assert zone_for_area("US", "Los Angeles") == "us_west"
    assert zone_for_area("US", "Phoenix") == "us_west"

    assert zone_family("us_east") == "north_america"
    assert zone_family("se_asia") == "asia"
    assert zone_family("british_isles") == "western_europe"
    assert zone_size_class("us_west") == "large"
    assert zone_size_class("dach_nordics") == "large"
    assert "north_america" in LARGE_ZONE_FAMILIES
    assert "western_europe" in LARGE_ZONE_FAMILIES


def test_large_scrape_zones_are_scheduled_last() -> None:
    large_zones = [z for z in ZONE_ORDER if zone_size_class(z) == "large"]
    # All large zones form a trailing block.
    assert ZONE_ORDER[-len(large_zones) :] == large_zones
    assert large_zones[0] == "british_isles"
    assert large_zones[-1] == "dach_nordics"


def test_beat_slots_cover_every_zone() -> None:
    assert set(ZONE_BEAT_SLOTS) == set(ZONE_ORDER) == set(SCRAPE_ZONES)
    assert markets_for_zone("us_east") == ["US"]
    assert markets_for_zone("us_west") == ["US"]
    assert "GB" in markets_for_zone("british_isles")
    assert "IE" in markets_for_zone("british_isles")
    assert len(iter_zone_areas("us_east")) + len(iter_zone_areas("us_west")) == 54


def test_zone_time_limit_is_inside_redis_visibility() -> None:
    assert ZONE_TASK_SOFT_TIME_LIMIT_SECONDS < ZONE_TASK_TIME_LIMIT_SECONDS
    assert ZONE_TASK_TIME_LIMIT_SECONDS < REDIS_VISIBILITY_TIMEOUT_SECONDS
    assert (
        celery_app.conf.broker_transport_options["visibility_timeout"]
        == REDIS_VISIBILITY_TIMEOUT_SECONDS
    )


def test_scrape_and_maintenance_use_separate_queues() -> None:
    routes = celery_app.conf.task_routes
    assert routes["app.workers.tasks.scrape_zone_retail"]["queue"] == SCRAPE_QUEUE
    assert routes["app.workers.tasks.retry_failed_scrape_city"]["queue"] == SCRAPE_QUEUE
    assert routes["app.workers.tasks.send_scrape_cycle_digest"]["queue"] == MAINTENANCE_QUEUE
    assert routes["app.workers.tasks.expire_past_due_deals"]["queue"] == MAINTENANCE_QUEUE
    schedule = celery_app.conf.beat_schedule
    assert schedule["scrape-zone-se_asia"]["options"]["queue"] == SCRAPE_QUEUE
    assert schedule["scrape-cycle-digest"]["options"]["queue"] == MAINTENANCE_QUEUE
    assert scrape_zone_retail.acks_late is True
    assert scrape_zone_retail.reject_on_worker_lost is True
    assert scrape_zone_retail.soft_time_limit == ZONE_TASK_SOFT_TIME_LIMIT_SECONDS
    assert scrape_zone_retail.time_limit == ZONE_TASK_TIME_LIMIT_SECONDS


def test_every_zone_stays_under_the_soft_time_budget() -> None:
    for zone_id in ZONE_ORDER:
        count = len(iter_zone_areas(zone_id))
        assert 0 < count <= 40, zone_id
        assert count <= MAX_ZONE_AREAS


def test_scrape_concurrency_defaults_to_six(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SCRAPE_CONCURRENCY", raising=False)
    assert scrape_concurrency() == 6
    assert scrape_concurrency("2") == 2
    assert scrape_concurrency("99") == 8
    assert scrape_concurrency("0") == 1
    assert scrape_concurrency("nope") == 6
