"""New Business Outreach: exclusion, email extraction, Overpass fallback, sheets."""

from __future__ import annotations

from types import SimpleNamespace

import httpx

from app.core.config import Settings
from app.services.new_business_outreach.constants import TAKEAWAYS, WINE_FARMS
from app.services.new_business_outreach.discover import emails_from_html, robots_allows_lines
from app.services.new_business_outreach.exclusion import ExclusionIndex, exclusion_reason
from app.services.new_business_outreach.overpass_query import query_overpass
from app.services.new_business_outreach.search import is_public_wine, venue_category
from app.services.new_business_outreach.sheets import export_new_leads, sheet_values
from app.services.new_business_outreach.storage import LeadSizeGuard, lead_storage_bytes
from app.services.new_business_outreach.tiles import TILES, europe_prefix_length, slice_tiles
from app.services.new_business_outreach.types import AcceptedLead

_RESTAURANTS = "Restaurants, Cafe's & Bistro's"


def _lead(**overrides: object) -> AcceptedLead:
    fields: dict[str, object] = {
        "business_name": "Oak Cafe",
        "country_code": "IE",
        "city": "Galway",
        "venue_category": _RESTAURANTS,
        "zone_id": "british_isles",
        "email": "owner@oak.example",
        "email_quality_score": 96,
        "website": "https://oak.example",
    }
    fields.update(overrides)
    return AcceptedLead(**fields)  # type: ignore[arg-type]


def test_legacy_outreach_flag_and_explicit_new_flag() -> None:
    assert (
        Settings(
            fishy_outreach_enabled=True,
            new_business_outreach_enabled=None,
        ).new_business_outreach_enabled
        is True
    )
    assert (
        Settings(
            fishy_outreach_enabled=True,
            new_business_outreach_enabled=False,
        ).new_business_outreach_enabled
        is False
    )
    assert Settings(new_business_outreach_weekday="monday").new_business_outreach_weekday == "monday"
    assert Settings().new_business_leads_max_mb == 100
    assert Settings().new_business_skip_own_ads is False


def test_exclusion_name_domain_unsubscribe_and_dedupe() -> None:
    index = ExclusionIndex()
    index.add_merchant(
        name="The Oak Cafe",
        country="IE",
        city="Galway",
        website="https://www.oak.example",
        email="desk@merchant.example",
    )
    index.add_contact(
        name="Pier Chipper",
        country="IE",
        city="Galway",
        website="https://pier.example",
        email="hello@pier.example",
    )
    index.add_unsubscribed_email("gone@chip.example")
    index.add_contact(
        name="Quiet Bar",
        country="IE",
        city="Cork",
        email="quiet@bar.example",
        suppressed=True,
    )

    assert exclusion_reason(_lead(website=None), index) == "already_on_site_name"
    assert (
        exclusion_reason(
            _lead(business_name="Different Name", email="new@oak.example"),
            index,
        )
        == "already_on_site_domain"
    )
    assert (
        exclusion_reason(
            _lead(
                business_name="Somewhere Else",
                email="desk@merchant.example",
                website="https://other.example",
            ),
            index,
        )
        == "already_on_site_email"
    )
    assert (
        exclusion_reason(
            _lead(business_name="New Chipper", email="hello@pier.example", website=None),
            index,
        )
        == "existing_contact"
    )
    assert (
        exclusion_reason(
            _lead(business_name="Fresh", email="gone@chip.example", website=None),
            index,
        )
        == "unsubscribed"
    )
    assert (
        exclusion_reason(
            _lead(
                business_name="Fresh Cork",
                city="Cork",
                email="quiet@bar.example",
                website=None,
            ),
            index,
        )
        == "suppressed"
    )
    assert (
        exclusion_reason(
            _lead(business_name="Oak Cafe", city="Cork", email="cork@oak.example", website=None),
            index,
        )
        is None
    )


def test_mailto_and_visible_emails_are_extracted() -> None:
    html = (
        '<a href="mailto:owner@oak.example?subject=Hi">Book</a>'
        " or info@oak.example"
    )
    found = emails_from_html(html)
    assert found[0] == "owner@oak.example"
    assert "info@oak.example" in found


def test_robots_disallow_is_honoured() -> None:
    lines = ["User-agent: *", "Disallow: /contact"]
    assert robots_allows_lines(lines, "https://oak.example/contact") is False
    assert robots_allows_lines(lines, "https://oak.example/menu") is True


def test_venue_types_cover_restaurants_chippers_and_cellar_doors() -> None:
    assert venue_category({"name": "Oak", "amenity": "restaurant"}) == _RESTAURANTS
    assert (
        venue_category({"name": "Leo Burdock", "amenity": "fast_food", "cuisine": "fish_and_chips"})
        == TAKEAWAYS
    )
    assert venue_category({"name": "The Chipper", "amenity": "restaurant"}) == TAKEAWAYS
    assert is_public_wine({"name": "Hill Farm", "craft": "winery"})
    assert venue_category({"name": "Hill Farm", "craft": "winery"}) == WINE_FARMS
    assert venue_category({"name": "Hill Cellar Door", "shop": "wine"}) == WINE_FARMS
    assert venue_category({"name": "City Bottle Shop", "shop": "wine"}) is None


def test_tiles_are_europe_first_and_checkpoint_wraps() -> None:
    prefix = europe_prefix_length()
    assert prefix > 10
    assert all(tile.europe for tile in TILES[:prefix])
    assert TILES[prefix].europe is False
    assert TILES[0].country_code == "IE"
    assert TILES[0].lead_zone == "british_isles"
    batch, nxt, wrapped = slice_tiles(len(TILES) - 1, 5)
    assert wrapped is True
    assert nxt == 0
    assert len(batch) == 1
    assert all(tile.south < tile.north and tile.west < tile.east for tile in TILES)


def test_lead_storage_share_and_guard() -> None:
    assert lead_storage_bytes(1_000, 10, 4) == 400
    assert lead_storage_bytes(1_000, 0, 4) == 0
    guard = LeadSizeGuard(1_000)
    guard.bytes = 900
    guard.note_inserts(1)
    assert guard.stopped is True


async def test_overpass_uses_the_next_mirror_after_a_failure() -> None:
    calls: list[str] = []

    async def post(endpoint: str, query: str, timeout: float) -> list[dict]:
        del query, timeout
        calls.append(endpoint)
        if "ok" not in endpoint:
            raise httpx.ConnectError("down")
        return [{"type": "node", "id": 1}]

    async def pause(_seconds: float) -> None:
        return None

    outcome = await query_overpass(
        "[out:json];",
        mirrors=("https://fail.example/interpreter", "https://ok.example/interpreter"),
        post=post,
        sleep=pause,
        rounds=1,
    )
    assert outcome.ok is True
    assert outcome.elements == [{"type": "node", "id": 1}]
    assert calls == [
        "https://fail.example/interpreter",
        "https://ok.example/interpreter",
    ]


async def test_overpass_failure_does_not_raise_when_every_mirror_fails() -> None:
    async def post(endpoint: str, query: str, timeout: float) -> list[dict]:
        del endpoint, query, timeout
        raise httpx.ConnectError("down")

    async def pause(_seconds: float) -> None:
        return None

    outcome = await query_overpass(
        "[out:json];",
        mirrors=("https://a.example/interpreter", "https://b.example/interpreter"),
        post=post,
        sleep=pause,
        rounds=1,
    )
    assert outcome.ok is False
    assert outcome.elements == []
    assert outcome.attempts == 2


def test_sheet_export_is_a_noop_without_credentials(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.new_business_outreach.sheets.get_settings",
        lambda: SimpleNamespace(
            google_service_account_json="",
            new_business_outreach_sheet_id="",
            new_business_outreach_drive_folder_id="",
        ),
    )
    result = export_new_leads([], week_label="2026-11-08")
    assert result["skipped"] is True
    assert result["reason"] == "unconfigured"


def test_sheet_export_writes_lean_columns_only(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.new_business_outreach.sheets.get_settings",
        lambda: SimpleNamespace(
            google_service_account_json='{"client_email":"sa@example.com","private_key":"SECRET"}',
            new_business_outreach_sheet_id="sheet123",
            new_business_outreach_drive_folder_id="folder-ignored",
        ),
    )
    calls: list[tuple] = []

    def request(method: str, url: str, json_body=None, params=None) -> dict:
        del params
        calls.append((method, url, json_body))
        if method == "GET":
            return {"sheets": [{"properties": {"title": "Sheet1"}}]}
        return {}

    rows = [
        {
            "name": "Oak Cafe",
            "type": _RESTAURANTS,
            "country": "IE",
            "region": "british_isles",
            "address": "1 Shop Street",
            "website": "https://oak.example",
            "email": "owner@oak.example",
            "source": "osm",
            "found date": "2026-11-08",
            "homepage_html": "<html>secret page</html>",
        }
    ]
    result = export_new_leads(rows, week_label="2026-11-08", request=request)
    assert result["ok"] is True
    assert result["mode"] == "tab"
    assert result["rows"] == 1
    blob = repr(calls)
    assert "owner@oak.example" in blob
    assert "homepage_html" not in blob
    assert "secret page" not in blob
    assert "SECRET" not in blob
    values = sheet_values(rows)
    assert values[0] == [
        "name",
        "type",
        "country",
        "region",
        "address",
        "website",
        "email",
        "source",
        "found date",
    ]
    assert "secret page" not in values[1]
