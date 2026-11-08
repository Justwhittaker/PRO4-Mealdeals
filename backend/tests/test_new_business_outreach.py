"""New Business Outreach: exclusion, email extraction, Overpass fallback, sheets."""

from __future__ import annotations

import socket
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import Settings
from app.services.new_business_outreach.constants import TAKEAWAYS, WINE_FARMS
from app.services.new_business_outreach.discover import (
    email_lookup_pages,
    emails_from_html,
    robots_allows_lines,
)
from app.services.new_business_outreach.exclusion import ExclusionIndex, exclusion_reason
from app.services.new_business_outreach.discover import _safe_get
from app.services.new_business_outreach.dry_run import run_new_business_dry_run
from app.services.new_business_outreach.overpass_query import OverpassOutcome, query_overpass
from app.services.new_business_outreach.run import (
    _prepare,
    run_new_business_outreach,
    run_zone_dry,
)
from app.services.new_business_outreach.search import is_public_wine, overpass_query, venue_category
from app.services.new_business_outreach.sheets import export_new_leads, sheet_values
from app.services.new_business_outreach.storage import LeadSizeGuard, lead_storage_bytes
from app.services.new_business_outreach.tiles import (
    MAX_TILE_RETRIES,
    TILES,
    OutreachTile,
    decode_pending,
    encode_pending,
    europe_prefix_length,
    quadrants,
    record_tile_outcome,
    should_subdivide,
    slice_tiles,
    venues_for_fetch,
)
from app.services.new_business_outreach.url_safety import (
    PublicOnlyTransport,
    redirect_target,
    url_is_safe,
)
from app.services.new_business_outreach.types import AcceptedLead, VenueCandidate
from app.services.new_business_outreach.website_queue import FetchBudget, attempt_website

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
    assert Settings().new_business_max_places_per_tile == 400
    assert Settings().new_business_website_fetches_per_run == 150


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
    france = [tile for tile in TILES if tile.country_code == "FR" and tile.name.startswith("France")]
    assert len(france) >= 12
    parent = france[0]
    children = quadrants(parent)
    assert len(children) == 4
    assert all(child.depth == parent.depth + 1 for child in children)
    assert all(child.span < parent.span for child in children)
    assert children[0].lead_zone == parent.lead_zone
    assert should_subdivide(parent, result_count=400, timed_out=False, max_places=400)
    assert should_subdivide(parent, result_count=400, timed_out=True, max_places=400) is False
    assert should_subdivide(parent, result_count=12, timed_out=False, max_places=400) is False
    tiny = OutreachTile(
        tile_id="tiny",
        country_code="FR",
        name="tiny",
        south=48.0,
        west=2.0,
        north=48.2,
        east=2.2,
        europe=True,
        lead_zone="france_benelux",
        depth=3,
    )
    assert tiny.span <= 0.5
    assert should_subdivide(tiny, result_count=400, timed_out=True, max_places=400) is False
    encoded = encode_pending(children)
    assert decode_pending(encoded) == children
    assert "out center tags 50" not in overpass_query(parent, limit=400)
    assert "out center tags 400" in overpass_query(parent, limit=400)


def test_website_budget_keeps_places_for_the_next_run() -> None:
    start, deferred = venues_for_fetch(10, 7)
    assert start == 2
    assert deferred == 8
    budget = FetchBudget(1)
    calls: list[str] = []

    def fetch(url: str):
        calls.append(url)
        return url, "owner@oak.example"

    candidate = VenueCandidate(
        business_name="Oak Cafe",
        country_code="IE",
        city="Galway",
        venue_category=_RESTAURANTS,
        zone_id="british_isles",
        website="https://oak.example",
        tile_id="ie-0",
    )
    skipped, status = attempt_website(candidate, FetchBudget(0), fetch=fetch)
    assert status == "skipped"
    assert skipped.website == "https://oak.example"
    assert calls == []
    updated, done = attempt_website(candidate, budget, fetch=fetch)
    assert done == "done"
    assert updated.emails[0] == "owner@oak.example"
    assert budget.remaining == 0
    assert calls == ["https://oak.example"]


def test_failed_overpass_tile_is_retried_before_the_cursor_moves() -> None:
    tile = TILES[0]
    failed = record_tile_outcome(
        index=0,
        pending=[],
        cycle=1,
        tile=tile,
        blocks_static=True,
        success=False,
        tile_count=len(TILES),
    )
    assert failed.index == 0
    assert failed.advanced is False
    assert failed.retrying is True
    assert failed.pending[0].tile_id == tile.tile_id
    assert failed.pending[0].retries == 1

    succeeded = record_tile_outcome(
        index=failed.index,
        pending=[],
        cycle=failed.cycle,
        tile=failed.pending[0],
        blocks_static=True,
        success=True,
        tile_count=len(TILES),
    )
    assert succeeded.advanced is True
    assert succeeded.index == 1
    assert succeeded.pending == ()


def test_overpass_outage_does_not_drop_tiles() -> None:
    tile = TILES[0]
    progress_index = 0
    pending = [tile]
    cycle = 1
    for _attempt in range(MAX_TILE_RETRIES):
        progress = record_tile_outcome(
            index=progress_index,
            pending=[],
            cycle=cycle,
            tile=pending[0],
            blocks_static=True,
            success=False,
            tile_count=len(TILES),
        )
        assert progress.index == 0
        assert progress.advanced is False
        assert progress.retrying is True
        pending = list(progress.pending)
        cycle = progress.cycle
    dropped = record_tile_outcome(
        index=0,
        pending=[],
        cycle=cycle,
        tile=pending[0],
        blocks_static=True,
        success=False,
        tile_count=len(TILES),
    )
    assert dropped.dropped is True
    assert dropped.index == 1


def test_website_urls_cannot_reach_private_hosts() -> None:
    public = lambda _host: ["1.1.1.1"]
    assert url_is_safe("http://127.0.0.1/latest") is False
    assert url_is_safe("http://127.1/") is False
    assert url_is_safe("http://2130706433/") is False
    assert url_is_safe("http://10.1.2.3/") is False
    assert url_is_safe("http://169.254.169.254/latest") is False
    assert url_is_safe("http://localhost/") is False
    assert url_is_safe("http://example.com:8080/", resolve=public) is False
    assert url_is_safe("ftp://example.com/", resolve=public) is False
    assert url_is_safe("https://rebind.example/", resolve=lambda _host: ["127.0.0.1"]) is False
    assert url_is_safe("https://example.com/menu", resolve=public) is True
    assert url_is_safe(redirect_target("https://example.com/a", "http://127.0.0.1/secret")) is False


def test_about_page_is_fetched_until_the_clock_stops() -> None:
    pages = email_lookup_pages("https://oak.example/menu")
    assert pages[0] == "https://oak.example/menu"
    assert "https://oak.example/contact" in pages
    assert "https://oak.example/about" in pages
    calls: list[str] = []

    def fetch(url: str):
        calls.append(url)
        return url, "no email here"

    def allow() -> bool:
        return len(calls) == 0

    candidate = VenueCandidate(
        business_name="Oak Cafe",
        country_code="IE",
        city="Galway",
        venue_category=_RESTAURANTS,
        zone_id="british_isles",
        website="https://oak.example/menu",
    )
    _updated, status = attempt_website(
        candidate,
        FetchBudget(5),
        fetch=fetch,
        allow=allow,
    )
    assert status == "yielded"
    assert calls == ["https://oak.example/menu"]


def test_lead_storage_share_and_guard() -> None:
    assert lead_storage_bytes(1_000, 10, 4) == 400
    assert lead_storage_bytes(1_000, 0, 4) == 0
    guard = LeadSizeGuard(1_000)
    guard.bytes = 900
    guard.note_inserts(1)
    assert guard.stopped is True


async def test_weekly_overpass_uses_the_configured_proxy_first(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.new_business_outreach.overpass_query.get_settings",
        lambda: SimpleNamespace(overpass_proxy_url="https://proxy.example/overpass"),
    )

    async def proxy(query: str, *, timeout: float, log_label: str) -> list[dict]:
        del query, timeout, log_label
        return [{"type": "node", "id": 7}]

    monkeypatch.setattr(
        "app.services.new_business_outreach.overpass_query._post_via_render_proxy",
        proxy,
    )
    outcome = await query_overpass("[out:json];")
    assert outcome.ok is True
    assert outcome.elements == [{"type": "node", "id": 7}]
    assert outcome.endpoint == "https://proxy.example/overpass"


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


async def test_overpass_timeout_is_flagged_separately_from_a_dead_mirror() -> None:
    async def post(endpoint: str, query: str, timeout: float) -> list[dict]:
        del endpoint, query, timeout
        raise httpx.TimeoutException("timed out")

    async def pause(_seconds: float) -> None:
        return None

    outcome = await query_overpass(
        "[out:json];",
        mirrors=("https://slow.example/interpreter",),
        post=post,
        sleep=pause,
        rounds=1,
    )
    assert outcome.ok is False
    assert outcome.timed_out is True
    assert outcome.elements == []
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
    assert outcome.timed_out is False


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


def test_overpass_timeout_does_not_advance_the_checkpoint(monkeypatch) -> None:
    """A timed-out tile stays put. It is not split and the cursor does not move."""
    start = 4
    saved: list[tuple[int, int, str]] = []
    queried: list[str] = []

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    def fake_open_session():
        return SimpleNamespace(dispose=lambda: None), _Session

    def fake_save(_session, *, next_tile_index: int, cycle: int, pending_subtiles: str | None = None):
        saved.append((next_tile_index, cycle, pending_subtiles or ""))

    def fake_discover(tile, *, limit: int):
        del limit
        queried.append(tile.tile_id)
        return [], OverpassOutcome(False, [], "timed out", None, 2, True)

    monkeypatch.setattr("app.services.new_business_outreach.run.open_session", fake_open_session)
    monkeypatch.setattr("app.services.new_business_outreach.run.load_checkpoint", lambda _session: (start, 2, ""))
    monkeypatch.setattr("app.services.new_business_outreach.run.save_checkpoint", fake_save)
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.load_stored_chain_signals",
        lambda _session: ({}, {}),
    )
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.LeadSizeGuard.refresh",
        lambda self, _session: None,
    )
    monkeypatch.setattr("app.services.new_business_outreach.run._discover_tile", fake_discover)
    monkeypatch.setattr("app.services.new_business_outreach.run.should_yield", lambda *_a, **_k: False)
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.export_new_leads",
        lambda *_a, **_k: {"skipped": True, "reason": "test"},
    )
    def _no_notify(*_args: object, **_kwargs: object) -> dict[str, bool]:
        raise AssertionError("outreach tried to notify")

    monkeypatch.setattr(
        "app.services.new_business_outreach.run.send_outreach_digest",
        lambda *_a, **_k: {"skipped": True},
    )
    monkeypatch.setattr("app.services.new_business_outreach.storage.send_ntfy", _no_notify)
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.get_settings",
        lambda: SimpleNamespace(
            new_business_outreach_enabled=False,
            new_business_outreach_weekday="sunday",
            new_business_skip_own_ads=False,
            new_business_tiles_per_run=5,
            new_business_max_places_per_tile=400,
            new_business_website_fetches_per_run=0,
            new_business_leads_max_mb=100,
        ),
    )

    summary = run_new_business_outreach()
    tile_id = TILES[start].tile_id
    assert queried == [tile_id]
    assert summary["next_tile_index"] == start
    assert summary["outreach_sends"] == 0
    assert summary["outreach_enabled"] is False
    assert saved
    index, cycle, pending_raw = saved[-1]
    assert index == start
    assert cycle == 2
    pending = decode_pending(pending_raw)
    assert [item.tile_id for item in pending] == [tile_id]
    assert pending[0].retries == 1
    assert all(not item.tile_id.startswith(f"{tile_id}-") for item in pending)


def test_ipv4_mapped_loopback_and_private_are_blocked(monkeypatch) -> None:
    assert url_is_safe("http://[::ffff:127.0.0.1]/latest") is False
    assert url_is_safe("http://[::ffff:10.0.0.1]/") is False
    assert url_is_safe("http://[::ffff:169.254.169.254]/latest/meta-data") is False
    assert url_is_safe("http://[::ffff:0:127.0.0.1]/") is False
    assert url_is_safe("http://[::ffff:0:10.0.0.1]/") is False
    assert url_is_safe("https://[2002:7f00:1::]/") is False
    assert url_is_safe("https://[2002:a00:1::]/") is False
    assert url_is_safe("http://[64:ff9b::7f00:1]/") is False
    assert url_is_safe("http://[64:ff9b::a00:1]/") is False
    assert url_is_safe("http://[::7f00:1]/") is False
    assert url_is_safe("http://[::a00:1]/") is False
    assert url_is_safe("https://cafe.example/", resolve=lambda _host: ["::ffff:127.0.0.1"]) is False
    assert url_is_safe("https://cafe.example/", resolve=lambda _host: ["::ffff:10.0.0.1"]) is False
    assert (
        url_is_safe(
            "https://cafe.example/",
            resolve=lambda _host: ["1.1.1.1", "::ffff:10.0.0.1"],
        )
        is False
    )
    assert url_is_safe("https://cafe.example/menu", resolve=lambda _host: ["1.1.1.1"]) is True
    hopped = redirect_target("https://cafe.example/menu", "http://[::ffff:127.0.0.1]/latest")
    assert url_is_safe(hopped) is False

    class _Boom(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"connected to {request.url}")

    transport = PublicOnlyTransport(resolve=lambda _host: ["::ffff:10.0.0.1", "1.1.1.1"])
    transport._inner = _Boom()
    with pytest.raises(httpx.ConnectError):
        transport.handle_request(httpx.Request("GET", "http://cafe.example/"))

    requested: list[str] = []

    class _Response:
        def __init__(self, status: int, headers: dict[str, str] | None = None, body: bytes = b"secret") -> None:
            self.status_code = status
            self.headers = headers or {}
            self.encoding = "utf-8"
            self._body = body

        def iter_bytes(self):
            yield self._body

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

    class _Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def stream(self, method: str, url: str, headers: dict | None = None):
            del method, headers
            requested.append(str(url))
            return _Response(302, {"location": "http://[::ffff:127.0.0.1]/latest"})

    monkeypatch.setattr("app.services.new_business_outreach.discover.httpx.Client", _Client)
    monkeypatch.setattr("app.services.new_business_outreach.discover.pace_host_sync", lambda _url: None)
    monkeypatch.setattr(
        "app.services.new_business_outreach.url_safety.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0))],
    )
    assert _safe_get("https://cafe.example/menu", limit=1000, check_robots=False) is None
    assert requested == ["https://cafe.example/menu"]


def test_chain_filter_reads_homepage_text() -> None:
    homepage = "<html><body>Own a franchise opportunities in every city</body></html>"
    stored = VenueCandidate(
        business_name="Oak Cafe",
        country_code="IE",
        city="Galway",
        venue_category=_RESTAURANTS,
        zone_id="british_isles",
        website="https://oak.example",
        emails=("owner@oak.example",),
        homepage_html=homepage,
    )
    prepared, stats = _prepare([stored])
    assert prepared == []
    assert stats["franchise_page"] == 1

    pages = {
        "https://oak.example": homepage,
        "https://oak.example/contact": "Write to owner@oak.example",
        "https://oak.example/about": "About the cafe",
    }

    def fetch(url: str):
        return url, pages[url]

    candidate = VenueCandidate(
        business_name="Oak Cafe",
        country_code="IE",
        city="Galway",
        venue_category=_RESTAURANTS,
        zone_id="british_isles",
        website="https://oak.example",
    )
    updated, status = attempt_website(candidate, FetchBudget(5), fetch=fetch)
    assert status == "done"
    assert updated.page_text is not None
    assert "franchise opportunit" in updated.page_text.lower()
    prepared, stats = _prepare([updated])
    assert prepared == []
    assert stats["franchise_page"] == 1


def test_zone_dry_run_fetches_websites_inside_the_budget(monkeypatch, capsys) -> None:
    calls: list[str] = []

    def fake_getaddrinfo(*_args, **_kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0))]

    def fake_get(url: str, *, limit: int, check_robots: bool):
        del limit, check_robots
        calls.append(url)
        if url.endswith("/robots.txt"):
            return 200, url, "User-agent: *\nAllow: /\n"
        if url.startswith("https://oak.example"):
            return 200, url, "<html>owner@oak.example</html>"
        return 200, url, "<html>no email here</html>"

    def fake_discover(tile, *, limit: int):
        del limit
        outcome = OverpassOutcome(True, [{"type": "node", "id": 1}], None, "mock", 1, False)
        shared = dict(
            country_code="IE",
            city="Galway",
            venue_category=_RESTAURANTS,
            zone_id=tile.lead_zone,
            tile_id=tile.tile_id,
        )
        return [
            VenueCandidate(business_name="Oak Cafe", website="https://oak.example", **shared),
            VenueCandidate(business_name="Pear Cafe", website="https://pear.example", **shared),
        ], outcome

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> bool:
            return False

        def add(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("dry run wrote a row")

        def add_all(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("dry run wrote a row")

        def delete(self, *_args: object, **_kwargs: object) -> None:
            raise AssertionError("dry run deleted a row")

        def commit(self) -> None:
            raise AssertionError("dry run committed")

        def flush(self) -> None:
            raise AssertionError("dry run flushed")

        def execute(self, *_args: object, **_kwargs: object):
            raise AssertionError("dry run queried the database")

    monkeypatch.setattr(
        "app.services.new_business_outreach.url_safety.socket.getaddrinfo",
        fake_getaddrinfo,
    )
    monkeypatch.setattr("app.services.new_business_outreach.discover._safe_get", fake_get)
    monkeypatch.setattr("app.services.new_business_outreach.run._discover_tile", fake_discover)
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.open_session",
        lambda: (SimpleNamespace(dispose=lambda: None), _Session),
    )
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.load_blocked_emails",
        lambda _session: (set(), set()),
    )
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.load_country_index",
        lambda _session, _country, **_kwargs: ExclusionIndex(),
    )
    def _no_notify(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dry run tried to notify")

    monkeypatch.setattr("app.services.new_business_outreach.storage.send_ntfy", _no_notify)
    monkeypatch.setattr("app.services.new_business_outreach.digest.send_ntfy", _no_notify)
    monkeypatch.setattr(
        "app.services.new_business_outreach.run.get_settings",
        lambda: SimpleNamespace(
            new_business_outreach_enabled=False,
            new_business_skip_own_ads=False,
            new_business_max_places_per_tile=400,
            new_business_website_fetches_per_run=3,
            new_business_leads_max_mb=100,
        ),
    )

    result = run_new_business_dry_run("ie-0")
    printed = capsys.readouterr().out
    assert result["ok"] is True
    assert result["summary"]["outreach_sends"] == 0
    assert result["summary"]["dry_run"] is True
    assert result["summary"]["with_email"] == 1
    assert result["summary"]["website_fetches"] == 1
    assert any(url.startswith("https://oak.example") and not url.endswith("/robots.txt") for url in calls)
    assert not any("pear.example" in url for url in calls)
    assert "With email: 1" in printed
    assert "Website fetches: 1" in printed
    assert "No database writes" in printed
    assert "No emails" in printed
    direct = run_zone_dry("ie-0")
    assert direct["with_email"] == 1
    assert direct["website_fetches"] == 1
