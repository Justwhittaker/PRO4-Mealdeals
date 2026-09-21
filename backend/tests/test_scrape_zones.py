"""Zone registry coverage / large-scrape split invariants."""

from __future__ import annotations

from app.scrapers.zones import (
    LARGE_ZONE_FAMILIES,
    SCRAPE_ZONES,
    ZONE_BEAT_SLOTS,
    ZONE_ORDER,
    markets_for_zone,
    validate_zone_coverage,
    zone_family,
    zone_for_country,
    zone_size_class,
)


def test_validate_zone_coverage() -> None:
    validate_zone_coverage()


def test_us_and_western_europe_are_large_family_splits() -> None:
    assert zone_for_country("US") == "us"
    assert zone_for_country("CA") == "canada_mexico_caribbean"
    assert zone_for_country("GB") == "british_isles"
    assert zone_for_country("FR") == "west_eu_core"
    assert zone_for_country("ES") == "south_europe"

    assert zone_family("us") == "north_america"
    assert zone_family("british_isles") == "western_europe"
    assert zone_size_class("us") == "large"
    assert zone_size_class("west_eu_core") == "large"
    assert "north_america" in LARGE_ZONE_FAMILIES
    assert "western_europe" in LARGE_ZONE_FAMILIES


def test_large_scrape_zones_are_scheduled_last() -> None:
    large_zones = [z for z in ZONE_ORDER if zone_size_class(z) == "large"]
    # All large zones form a trailing block.
    assert ZONE_ORDER[-len(large_zones) :] == large_zones
    assert large_zones[0] == "british_isles"
    assert large_zones[-1] == "west_eu_core"


def test_beat_slots_cover_every_zone() -> None:
    assert set(ZONE_BEAT_SLOTS) == set(ZONE_ORDER) == set(SCRAPE_ZONES)
    assert markets_for_zone("us") == ["US"]
    assert "GB" in markets_for_zone("british_isles")
    assert "IE" in markets_for_zone("british_isles")
