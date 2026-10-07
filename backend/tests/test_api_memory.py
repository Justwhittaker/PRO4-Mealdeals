"""Guards for web-process memory: startup imports and the scrape report."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.api.v1.endpoints.deals import _FEED_PAGE_OPTIONS
from app.core.memory import release_heap_to_os
from app.services.city_coords import merged_city_coords
from app.services.ingest import CITY_COORDS
from app.services.scrape_report import (
    active_deal_location_stmt,
    breakdown_from_rows,
    contact_category_stmt,
)

_BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_api_startup_does_not_import_scraper_or_celery() -> None:
    script = """
import app.main
forbidden = [
    "celery",
    "app.scrapers.global_retail",
    "app.workers.tasks",
    "app.workers.celery_app",
    "app.services.scrape_runner",
    "app.services.ingest",
    "app.scrapers.fetch_guard",
    "app.scrapers.offer_links",
    "bs4",
    "lxml",
    "lxml.etree",
    "playwright",
]
loaded = [name for name in forbidden if name in __import__("sys").modules]
print(",".join(loaded))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(_BACKEND_DIR)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    loaded = [name for name in completed.stdout.strip().split(",") if name]
    assert loaded == []


def test_report_queries_do_not_select_deal_graphs() -> None:
    deal_sql = str(active_deal_location_stmt()).lower()
    contact_sql = str(contact_category_stmt()).lower()
    assert "deal_items" not in deal_sql
    assert "deal_translations" not in deal_sql
    assert "image_url" not in deal_sql
    assert "merchants" in deal_sql
    assert "locations" in deal_sql
    assert "about_blurb" not in contact_sql
    assert "venue_category" in contact_sql


def test_breakdown_from_rows_matches_contact_then_name_rules() -> None:
    contacts = [("IE", "Dublin", "Cafe Nero", "Deli's and Grocers")]
    deals = [
        ("ie", "Dublin", "Cafe Nero"),
        ("IE", "Dublin", "The Quays Bar"),
        ("IE", None, "Hilton Garden Inn"),
        ("IE", "", "Mystery Venue"),
    ]
    rows = {
        (row["country"], row["city"], row["category"]): row["deals"]
        for row in breakdown_from_rows(contacts, deals)
    }
    assert rows[("IE", "Dublin", "Deli's and Grocers")] == 1
    assert rows[("IE", "Dublin", "Clubs, Bars & Pubs")] == 1
    assert rows[("IE", "Unknown", "Hotels, Resorts & B&B's")] == 1
    assert rows[("IE", "Unknown", "Restaurants, Cafe's & Bistro's")] == 1


def test_feed_page_skips_deal_items() -> None:
    source = (_BACKEND_DIR / "app/api/v1/endpoints/deals.py").read_text()
    assert ".options(*_FEED_PAGE_OPTIONS)" in source
    strategies = [option.context[0].strategy for option in _FEED_PAGE_OPTIONS]
    paths = [str(option.context[0].path) for option in _FEED_PAGE_OPTIONS]
    assert (("lazy", "noload"),) in strategies
    assert any("items" in path for path in paths)
    assert (("lazy", "selectin"),) in strategies
    assert any("translations" in path for path in paths)


def test_merged_city_coords_match_ingest_index() -> None:
    merged = merged_city_coords()
    assert merged == CITY_COORDS
    assert ("GB", "London") in merged
    assert ("IE", "Killarney") in merged


def test_release_heap_to_os_is_safe() -> None:
    release_heap_to_os()
