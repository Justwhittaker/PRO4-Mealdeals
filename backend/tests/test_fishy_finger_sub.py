"""Fishy Finger Sub: chains, email quality, outreach order, digest, schedule."""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql

from app.api.v1.endpoints.scrapers import PlanInfo
from app.scrapers.categories import CATEGORY_ORDER
from app.scrapers.local_discovery import osm_contact_from_element
from app.scrapers.zones import (
    MAINTENANCE_QUEUE,
    SCRAPE_QUEUE,
    ZONE_BEAT_STAGGER_MINUTES,
    ZONE_CYCLE_BASE_HOURS,
    ZONE_ORDER,
)
from app.services.fishy_finger.chains import (
    BRAND_CITY_THRESHOLD,
    DOMAIN_VENUE_THRESHOLD,
    ChainSignals,
    chain_exclusion_reason,
)
from app.services.fishy_finger.constants import FISHY_FINGER_SEGMENT
from app.services.fishy_finger.digest import (
    category_digest_label,
    format_fishy_digest,
    no_specials_breakdown,
    percentage_breakdown,
    zone_digest_label,
)
from app.services.fishy_finger.email_quality import pick_best_email, score_email
from app.services.fishy_finger.ezine import (
    PRIORITY_INTRO_MONTHS,
    PRIORITY_INTRO_PRICE_EUR,
    PRIORITY_RECURRING_PRICE_EUR,
    PRIORITY_SLOTS,
    build_fishy_ezine,
)
from app.services.fishy_finger.leads import (
    enrich_candidates,
    insert_fishy_lead,
    lead_is_known,
    select_fishy_leads,
)
from app.services.fishy_finger.dry_run import run_fishy_dry_run
from app.services.fishy_finger.schedule import (
    DUBLIN,
    EU_ZONE_ORDER,
    FISHY_DIGEST_HOUR,
    FISHY_DIGEST_MINUTE,
    EuropeDublinWeekly,
    fishy_week_start,
    fishy_zone_clock,
    fishy_zone_order,
    lead_region,
    next_dublin_sunday_after,
)
from app.services.fishy_finger.specials import (
    classify_site_specials,
    fetch_specials_probes,
    specials_probe_urls,
)
from app.services.fishy_finger.types import AcceptedLead, VenueCandidate
from app.services.merchant_outreach import (
    outreach_batch_statement,
    rank_outreach_candidates,
)
from app.workers.celery_app import celery_app

_RESTAURANTS = "Restaurants, Cafe's & Bistro's"


def _venue(**overrides: object) -> VenueCandidate:
    fields: dict[str, object] = {
        "business_name": "Oak Cafe",
        "country_code": "IE",
        "city": "Galway",
        "venue_category": _RESTAURANTS,
        "zone_id": "british_isles",
        "website": "https://oak.example",
        "emails": ("owner@oak.example",),
    }
    fields.update(overrides)
    return VenueCandidate(**fields)  # type: ignore[arg-type]


def _contact(**overrides: object) -> SimpleNamespace:
    fields: dict[str, object] = {
        "email": "owner@oak.example",
        "source_segment": None,
        "outreach_unsubscribed_at": None,
        "outreach_excluded_at": None,
        "last_outreach_sent_at": None,
        "last_scraped_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "email_quality_score": None,
        "lead_zone": None,
        "has_site_specials": None,
        "business_name": "Oak Cafe",
        "website": "https://oak.example",
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_known_chain_names_are_excluded() -> None:
    reason = chain_exclusion_reason(
        business_name="McDonald's Galway",
        website="https://mcdonalds.example",
        signals=ChainSignals(),
    )
    assert reason == "known_chain"
    assert (
        chain_exclusion_reason(
            business_name="Harbour Restaurant Group",
            signals=ChainSignals(),
        )
        == "group_name"
    )
    assert (
        chain_exclusion_reason(
            business_name="Oak Cafe",
            osm_brand_wikidata="Q12345",
            signals=ChainSignals(),
        )
        == "brand_wikidata"
    )


def test_franchise_page_is_excluded() -> None:
    assert (
        chain_exclusion_reason(
            business_name="Oak Cafe",
            website="https://oak.example/locations/ireland",
            signals=ChainSignals(),
        )
        == "franchise_page"
    )
    accepted, stats = select_fishy_leads(
        [
            _venue(
                page_text="Own a franchise opportunities in every city",
                emails=("info@oak.example",),
            )
        ]
    )
    assert accepted == []
    assert stats["franchise_page"] == 1


def test_brand_in_many_cities_is_excluded() -> None:
    assert BRAND_CITY_THRESHOLD == 3
    cities = ["Dublin", "Cork", "Galway"]
    venues = [
        _venue(
            business_name="Burger Palace",
            city=city,
            website=f"https://{city.lower()}.burgerpalace.example",
            emails=(f"owner@{city.lower()}.burgerpalace.example",),
        )
        for city in cities
    ]
    accepted, stats = select_fishy_leads(venues)
    assert accepted == []
    assert stats["multi_city_brand"] == 3

    kept, _stats = select_fishy_leads(venues[:2])
    assert len(kept) == 2

    # A third city already stored from an earlier week tips the same brand over.
    stored = {"burger palace": {("IE", "limerick")}}
    caught, caught_stats = select_fishy_leads(
        venues[:2],
        extra_brand_cities=stored,
    )
    assert caught == []
    assert caught_stats["multi_city_brand"] == 2


def test_shared_corporate_domain_is_excluded_and_builders_are_not() -> None:
    assert DOMAIN_VENUE_THRESHOLD == 4
    grouped = [
        _venue(
            business_name=f"Cafe {index}",
            city=city,
            website=f"https://group.example/{index}",
            emails=(f"owner{index}@group.example",),
        )
        for index, city in enumerate(["Dublin", "Cork", "Galway", "Limerick"])
    ]
    accepted, stats = select_fishy_leads(grouped)
    assert accepted == []
    assert stats["shared_corporate_domain"] == 4

    builders = [
        _venue(
            business_name=f"Independent {index}",
            city="Galway",
            website=f"https://cafe{index}.wixsite.com/site",
            emails=(f"hello@cafe{index}.example",),
        )
        for index in range(4)
    ]
    kept, builder_stats = select_fishy_leads(builders)
    assert len(kept) == 4
    assert "shared_corporate_domain" not in builder_stats


def test_independent_with_owner_email_is_kept() -> None:
    accepted, stats = select_fishy_leads([_venue()])
    assert stats["kept"] == 1
    assert accepted[0].email == "owner@oak.example"
    assert accepted[0].email_quality_score == score_email("owner@oak.example").score
    assert accepted[0].venue_category in CATEGORY_ORDER


def test_email_preference_and_rejections() -> None:
    owner = score_email("owner@oak.example")
    marketing = score_email("marketing@oak.example")
    named = score_email("jane.smith@oak.example")
    hello = score_email("hello@oak.example")
    info = score_email("info@oak.example")
    bookings = score_email("bookings@oak.example")
    support_own = score_email("support@oak.example")
    assert owner.score > marketing.score > named.score
    assert named.score > hello.score > info.score > bookings.score
    assert bookings.accepted
    assert support_own.accepted
    assert support_own.score < info.score

    for local in (
        "noreply",
        "no-reply",
        "donotreply",
        "mailer-daemon",
        "privacy",
        "legal",
        "abuse",
        "jobs",
        "careers",
    ):
        verdict = score_email(f"{local}@oak.example")
        assert not verdict.accepted, local

    assert not score_email("support@wix.com").accepted
    assert not score_email("jane@opentable.com").accepted
    assert not score_email("reservations@thefork.com").accepted

    best = pick_best_email(
        ("noreply@oak.example", "info@oak.example", "owner@oak.example")
    )
    assert best.email == "owner@oak.example"
    assert best.accepted


def test_homepage_email_is_used_when_osm_has_none() -> None:
    venue = _venue(emails=(), website="https://oak.example")

    def _fetch(url: str) -> tuple[str, str]:
        assert url == "https://oak.example"
        return url, "<p>Email owner@oak.example for a table</p>"

    enriched = enrich_candidates([venue], fetch=_fetch)
    accepted, _stats = select_fishy_leads(enriched)
    assert accepted[0].email == "owner@oak.example"


def test_outreach_fills_with_fishy_leads_then_existing_order() -> None:
    now = datetime(2026, 10, 9, tzinfo=timezone.utc)
    fishy_high = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="owner@a.example",
        email_quality_score=96,
    )
    fishy_low = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="info@b.example",
        email_quality_score=80,
    )
    regular_new = _contact(
        email="hello@c.example",
        email_quality_score=99,
        last_scraped_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    regular_older_scrape = _contact(
        email="hello@d.example",
        last_scraped_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )
    already_sent = _contact(
        email="hello@e.example",
        last_outreach_sent_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    fishy_recent = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="owner@recent.example",
        email_quality_score=96,
        last_outreach_sent_at=now - timedelta(days=3),
    )
    unsubscribed = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="owner@unsub.example",
        email_quality_score=96,
        outreach_unsubscribed_at=now,
    )
    batch = rank_outreach_candidates(
        [
            already_sent,
            fishy_low,
            unsubscribed,
            fishy_recent,
            regular_older_scrape,
            regular_new,
            fishy_high,
        ],
        now=now,
        min_days=28,
        max_rows=95,
    )
    assert [row.email for row in batch] == [
        "owner@a.example",
        "info@b.example",
        "hello@c.example",
        "hello@d.example",
        "hello@e.example",
    ]


def test_drip_order_is_eu_no_specials_then_quality() -> None:
    now = datetime(2026, 10, 9, tzinfo=timezone.utc)
    eu_low = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="low@eu.example",
        lead_zone="iberia",
        has_site_specials=False,
        email_quality_score=70,
        last_scraped_at=datetime(2026, 10, 8, tzinfo=timezone.utc),
    )
    eu_high = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="high@eu.example",
        lead_zone="british_isles",
        has_site_specials=False,
        email_quality_score=90,
    )
    eu_resent = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="again@eu.example",
        lead_zone="france_benelux",
        has_site_specials=False,
        email_quality_score=60,
        last_outreach_sent_at=now - timedelta(days=40),
    )
    other_false = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="none@us.example",
        lead_zone="us_east",
        has_site_specials=False,
        email_quality_score=99,
    )
    remaining = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="listed@eu.example",
        lead_zone="dach_nordics",
        has_site_specials=True,
        email_quality_score=100,
    )
    unknown = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="unknown@eu.example",
        lead_zone="eastern_europe",
        has_site_specials=None,
        email_quality_score=95,
    )
    never = _contact(email="backlog@new.example", email_quality_score=100)
    cooled = _contact(
        email="backlog@old.example",
        email_quality_score=100,
        last_outreach_sent_at=now - timedelta(days=40),
    )
    too_soon = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="soon@eu.example",
        lead_zone="british_isles",
        has_site_specials=False,
        email_quality_score=100,
        last_outreach_sent_at=now - timedelta(days=3),
    )
    unsubscribed = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="unsub@eu.example",
        lead_zone="british_isles",
        has_site_specials=False,
        email_quality_score=100,
        outreach_unsubscribed_at=now,
    )
    batch = rank_outreach_candidates(
        [
            cooled,
            never,
            unknown,
            remaining,
            other_false,
            eu_resent,
            too_soon,
            unsubscribed,
            eu_low,
            eu_high,
        ],
        now=now,
        min_days=28,
        max_rows=95,
    )
    assert [row.email for row in batch] == [
        "high@eu.example",
        "low@eu.example",
        "again@eu.example",
        "none@us.example",
        "listed@eu.example",
        "unknown@eu.example",
        "backlog@new.example",
        "backlog@old.example",
    ]


def test_quality_does_not_jump_drip_groups() -> None:
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    never = _contact(email="info@new.example", email_quality_score=1)
    cooled = _contact(
        email="hello@old.example",
        email_quality_score=99,
        last_outreach_sent_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    batch = rank_outreach_candidates(
        [cooled, never],
        now=now,
        min_days=28,
        max_rows=95,
    )
    assert [row.email for row in batch] == ["info@new.example", "hello@old.example"]


def test_outreach_keeps_gap_unsubscribe_merchant_and_cap() -> None:
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    exactly_gap = _contact(
        email="gap@oak.example",
        last_outreach_sent_at=now - timedelta(days=28),
    )
    just_outside = _contact(
        email="ready@oak.example",
        last_outreach_sent_at=now - timedelta(days=28, seconds=1),
    )
    batch = rank_outreach_candidates(
        [exactly_gap, just_outside],
        now=now,
        min_days=28,
        max_rows=95,
    )
    assert [row.email for row in batch] == ["ready@oak.example"]

    merchant = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="owner@signed-up.example",
        email_quality_score=96,
    )
    assert (
        rank_outreach_candidates(
            [merchant],
            now=now,
            min_days=28,
            max_rows=95,
            merchant_emails={"owner@signed-up.example"},
        )
        == []
    )

    rows = [
        _contact(
            source_segment=FISHY_FINGER_SEGMENT,
            email=f"owner{index}@venue{index}.example",
            email_quality_score=100 - index,
        )
        for index in range(10)
    ]
    capped = rank_outreach_candidates(rows, now=now, min_days=28, max_rows=3)
    assert [row.email for row in capped] == [
        "owner0@venue0.example",
        "owner1@venue1.example",
        "owner2@venue2.example",
    ]


def test_outreach_sql_orders_fishy_leads_first() -> None:
    stmt = outreach_batch_statement(datetime(2026, 1, 1, tzinfo=timezone.utc), 95)
    sql = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "fishy_finger_sub" in sql
    assert "email_quality_score" in sql
    assert "has_site_specials" in sql
    assert "british_isles" in sql
    assert "LIMIT 95" in sql


def test_digest_breakdown_percentages() -> None:
    assert zone_digest_label("australia") == "Australia"
    assert category_digest_label("Wine Farms & Entertainment Venues") == "Wine farms"
    assert category_digest_label("Restaurants, Cafe's & Bistro's") == "Restaurants"

    by_zone = percentage_breakdown(
        {"Australia": 30, "Eastern Europe": 20, "British Isles": 50}
    )
    by_category = percentage_breakdown(
        {"Restaurants": 50, "Wine farms": 15, "Bars & pubs": 35}
    )
    body = format_fishy_digest(
        {
            "week_label": "2026-10-11",
            "net_new_lead_emails": 100,
            "unsubscribed": 7,
            "still_to_email": 420,
            "by_zone": by_zone,
            "by_category": by_category,
        }
    )
    assert "Net new lead emails: 100" in body
    assert "Unsubscribed: 7" in body
    assert "Still to email: 420" in body
    assert "Australia: 30% (30)" in body
    assert "Eastern Europe: 20% (20)" in body
    assert "Restaurants: 50% (50)" in body
    assert "Wine farms: 15% (15)" in body
    assert body.index("By zone:") < body.index("By category:")


def test_week_window_follows_dublin_sunday_morning() -> None:
    winter = datetime(2026, 1, 4, 10, 0, tzinfo=timezone.utc)
    assert fishy_week_start(winter) == datetime(2026, 1, 4, 8, 0, tzinfo=timezone.utc)
    early = datetime(2026, 1, 4, 7, 0, tzinfo=timezone.utc)
    assert fishy_week_start(early) == datetime(2025, 12, 28, 8, 0, tzinfo=timezone.utc)
    summer = datetime(2026, 3, 29, 8, 30, tzinfo=DUBLIN)
    assert fishy_week_start(summer) == datetime(2026, 3, 29, 7, 0, tzinfo=timezone.utc)


def test_sunday_schedule_is_dst_aware_and_separate_from_deal_cycles() -> None:
    assert ZONE_CYCLE_BASE_HOURS == (7, 19)
    winter_slot = datetime(2026, 1, 4, 8, 0, tzinfo=DUBLIN)
    assert winter_slot.astimezone(timezone.utc) == datetime(
        2026, 1, 4, 8, 0, tzinfo=timezone.utc
    )
    summer_slot = datetime(2026, 3, 29, 8, 0, tzinfo=DUBLIN)
    assert summer_slot.astimezone(timezone.utc) == datetime(
        2026, 3, 29, 7, 0, tzinfo=timezone.utc
    )
    before_summer = datetime(2026, 3, 29, 6, 30, tzinfo=timezone.utc)
    nxt = next_dublin_sunday_after(before_summer, hour=8, minute=0)
    assert nxt.astimezone(timezone.utc) == summer_slot.astimezone(timezone.utc)

    due_now = datetime(2026, 1, 4, 8, 5, tzinfo=timezone.utc)
    schedule = EuropeDublinWeekly(hour=8, minute=0, nowfun=lambda: due_now)
    assert schedule.is_due(datetime(2025, 12, 28, 8, 0, tzinfo=timezone.utc))[0] is True
    assert schedule.is_due(datetime(2026, 1, 4, 8, 0, tzinfo=timezone.utc))[0] is False

    monday_afternoon = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    late = EuropeDublinWeekly(hour=8, minute=0, nowfun=lambda: monday_afternoon)
    assert late.is_due(datetime(2025, 12, 28, 8, 0, tzinfo=timezone.utc))[0] is False

    order = fishy_zone_order()
    assert order[: len(EU_ZONE_ORDER)] == list(EU_ZONE_ORDER)
    assert set(EU_ZONE_ORDER) == {
        zone_id for zone_id in order if lead_region(zone_id) == "EU"
    }
    assert lead_region("us_east") == "NA"
    assert lead_region("australia") == "Other"
    clocks = [fishy_zone_clock(zone_id) for zone_id in order]
    assert clocks[0] == (8, 0)
    assert clocks[1] == (8, ZONE_BEAT_STAGGER_MINUTES)
    minutes = [hour * 60 + minute for hour, minute in clocks]
    assert minutes == sorted(minutes)
    assert minutes[-1] - minutes[0] == (len(order) - 1) * ZONE_BEAT_STAGGER_MINUTES
    assert fishy_zone_clock("british_isles") == (8, 0)
    assert fishy_zone_clock("mena") == (9, 0)

    for zone_id in ZONE_ORDER:
        fishy = celery_app.conf.beat_schedule[f"fishy-finger-{zone_id}"]
        deal = celery_app.conf.beat_schedule[f"scrape-zone-{zone_id}"]
        assert fishy["task"] == "app.workers.tasks.scrape_fishy_finger_zone"
        assert fishy["kwargs"] == {"zone_id": zone_id}
        assert isinstance(fishy["schedule"], EuropeDublinWeekly)
        assert (fishy["schedule"].hour, fishy["schedule"].minute) == fishy_zone_clock(
            zone_id
        )
        assert fishy["options"]["queue"] == SCRAPE_QUEUE
        assert deal["task"] == "app.workers.tasks.scrape_zone_retail"
        assert not isinstance(deal["schedule"], EuropeDublinWeekly)

    digest = celery_app.conf.beat_schedule["fishy-finger-digest"]
    assert digest["task"] == "app.workers.tasks.send_fishy_finger_digest"
    assert isinstance(digest["schedule"], EuropeDublinWeekly)
    assert (digest["schedule"].hour, digest["schedule"].minute) == (
        FISHY_DIGEST_HOUR,
        FISHY_DIGEST_MINUTE,
    )
    assert digest["options"]["queue"] == MAINTENANCE_QUEUE
    routes = celery_app.conf.task_routes
    assert routes["app.workers.tasks.scrape_fishy_finger_zone"]["queue"] == SCRAPE_QUEUE
    assert (
        routes["app.workers.tasks.send_fishy_finger_digest"]["queue"]
        == MAINTENANCE_QUEUE
    )


def test_ezine_uses_live_count_plan_and_one_cta() -> None:
    plan = PlanInfo()
    assert plan.intro_price_eur == PRIORITY_INTRO_PRICE_EUR
    assert plan.intro_months == PRIORITY_INTRO_MONTHS
    assert plan.intro_deal_slots == PRIORITY_SLOTS
    assert plan.recurring_price_eur == PRIORITY_RECURRING_PRICE_EUR

    contact = SimpleNamespace(business_name="Oak <Cafe>", city="Galway")
    subject, text_body, html_body = build_fishy_ezine(
        contact,  # type: ignore[arg-type]
        unsubscribe_url="https://api.example/unsub?token=abc",
        dashboard_url="https://dineadeal.com/dashboard",
        active_deals=1234,
    )
    assert subject == "List Oak <Cafe> on DineADeal"
    assert "1,234 live deals" in text_body
    assert "DineADeal is where diners look for offers" in text_body
    assert "no commission" in text_body
    assert "€20 for 3 months with 3 hero slots" in text_body
    assert "Friday newsletter" in text_body
    assert "List your business: https://dineadeal.com/dashboard" in text_body
    assert "Unsubscribe: https://api.example/unsub?token=abc" in text_body
    assert "testimonial" not in text_body.lower()
    assert "viewport" in html_body
    assert "List your business" in html_body
    assert "Oak &lt;Cafe&gt;" in html_body
    assert html_body.count("https://dineadeal.com/dashboard") == 1

    _subject, quiet, _html = build_fishy_ezine(
        contact,  # type: ignore[arg-type]
        unsubscribe_url="https://api.example/unsub?token=abc",
        dashboard_url="https://dineadeal.com/dashboard",
        active_deals=None,
    )
    assert "1,234" not in quiet
    assert "Diners browse live deals on DineADeal." in quiet
    assert "isn't promoting specials" not in text_body
    assert "isn't promoting specials" not in quiet


def test_osm_contacts_use_existing_categories() -> None:
    cafe = osm_contact_from_element(
        {
            "tags": {
                "name": "Oak Cafe",
                "amenity": "cafe",
                "website": "https://oak.example",
                "email": "hello@oak.example",
            }
        }
    )
    assert cafe is not None
    assert cafe["venue_category"] == _RESTAURANTS
    assert cafe["emails"] == ("hello@oak.example",)

    winery = osm_contact_from_element(
        {
            "tags": {
                "name": "Hill Farm",
                "craft": "winery",
                "website": "https://hill.example",
                "contact:email": "owner@hill.example",
            }
        }
    )
    assert winery is not None
    assert winery["venue_category"] == "Wine Farms & Entertainment Venues"


def test_insert_stores_fishy_segment_zone_and_score() -> None:
    class _Session:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, row: object) -> None:
            self.added.append(row)

        def flush(self) -> None:
            return None

    lead = AcceptedLead(
        business_name="Oak Cafe",
        country_code="IE",
        city="Galway",
        venue_category=_RESTAURANTS,
        zone_id="british_isles",
        email="owner@oak.example",
        email_quality_score=96,
        website="https://oak.example",
        phone=None,
        has_site_specials=False,
        specials_checked_at=datetime(2026, 11, 8, 8, 0, tzinfo=timezone.utc),
    )
    session = _Session()
    row = insert_fishy_lead(session, lead)  # type: ignore[arg-type]
    assert session.added == [row]
    assert row.source_segment == FISHY_FINGER_SEGMENT
    assert row.lead_zone == "british_isles"
    assert row.email_quality_score == 96
    assert row.has_site_specials is False
    assert row.specials_checked_at == datetime(2026, 11, 8, 8, 0, tzinfo=timezone.utc)
    assert row.last_outreach_sent_at is None
    assert row.country_code == "IE"
    assert row.city == "Galway"
    assert lead_is_known(lead, {("email", "owner@oak.example")})
    assert not lead_is_known(lead, set())


def test_migration_adds_fishy_columns() -> None:
    backend = Path(__file__).resolve().parents[1]
    path = backend / "alembic" / "versions" / "018_fishy_finger_sub.py"
    text = path.read_text(encoding="utf-8")
    assert 'revision: str = "018_fishy_finger_sub"' in text
    assert 'down_revision: Union[str, None] = "017_oom_feed_indexes"' in text
    assert "SET LOCAL statement_timeout = 0" in text
    assert "server_default" not in text
    assert "nullable=True" in text
    assert "source_segment" in text
    assert "lead_zone" in text
    assert "email_quality_score" in text
    assert "has_site_specials" in text
    assert "specials_checked_at" in text
    assert not (backend / "alembic" / "versions" / "016_fishy_finger_sub.py").exists()
    script = ScriptDirectory.from_config(Config(str(backend / "alembic.ini")))
    assert script.get_heads() == ["018_fishy_finger_sub"]


_OFFER_HTML = (
    "<html><body><a href='/deals/lunch-special'>Lunch deal 20% off</a></body></html>"
)
_EMPTY_HTML = "<html><body>Welcome to our cafe. Open Tuesday.</body></html>"


def _probe_get(status_for_path: dict[str, tuple[int | None, str, str | None]]):
    calls: list[str] = []

    def get(url: str) -> tuple[int | None, str | None, str | None]:
        calls.append(url)
        path = urlparse(url).path
        status, html, error = status_for_path.get(path, (404, "", None))
        return status, html, error

    return calls, get


def test_specials_probes_use_only_offers_specials_and_deals() -> None:
    urls = specials_probe_urls("https://oak.example/en")
    assert [urlparse(url).path for url in urls] == [
        "/en/offers",
        "/en/specials",
        "/en/deals",
    ]
    plain = specials_probe_urls("https://oak.example")
    assert [urlparse(url).path for url in plain] == ["/offers", "/specials", "/deals"]
    joined = " ".join(plain)
    assert "/menu" not in joined
    assert "/promotions" not in joined
    assert "/vouchers" not in joined


def test_all_404_probes_flag_no_specials() -> None:
    calls, get = _probe_get({})
    probes = fetch_specials_probes("https://oak.example", get=get)
    assert [urlparse(url).path for url in calls] == ["/offers", "/specials", "/deals"]
    assert classify_site_specials(probes) is False
    empty_calls, empty_get = _probe_get(
        {
            "/offers": (200, _EMPTY_HTML, None),
            "/specials": (404, "", None),
            "/deals": (200, _EMPTY_HTML, None),
        }
    )
    empty = fetch_specials_probes("https://oak.example", get=empty_get)
    assert len(empty_calls) == 3
    assert classify_site_specials(empty) is False


def test_any_offer_flags_specials_without_extra_paths() -> None:
    calls, get = _probe_get(
        {
            "/offers": (404, "", None),
            "/specials": (200, _OFFER_HTML, None),
            "/deals": (500, "", None),
        }
    )
    probes = fetch_specials_probes("https://oak.example", get=get)
    assert len(calls) == 3
    assert classify_site_specials(probes) is True
    missed = fetch_specials_probes(
        "https://oak.example",
        get=_probe_get({})[1],
    )
    assert (
        classify_site_specials(
            missed,
            crawled_pages=(("https://oak.example/menu", _OFFER_HTML),),
        )
        is True
    )
    snippet = "<html><body><p>Happy hour from five.</p></body></html>"
    assert (
        classify_site_specials(
            missed,
            crawled_pages=(("https://oak.example/", snippet),),
        )
        is True
    )


def test_probe_error_leaves_specials_unknown() -> None:
    _calls, get = _probe_get(
        {
            "/offers": (404, "", None),
            "/specials": (200, _EMPTY_HTML, None),
            "/deals": (None, "", "timeout"),
        }
    )
    probes = fetch_specials_probes("https://oak.example", get=get)
    assert classify_site_specials(probes) is None
    server = fetch_specials_probes(
        "https://oak.example",
        get=_probe_get({"/offers": (503, "", None), "/specials": (404, "", None)})[1],
    )
    assert classify_site_specials(server) is None


def test_no_specials_pitch_opens_with_a_free_listing() -> None:
    contact = SimpleNamespace(
        business_name="Oak <Cafe>",
        city="Galway",
        has_site_specials=False,
    )
    _subject, text_body, html_body = build_fishy_ezine(
        contact,  # type: ignore[arg-type]
        unsubscribe_url="https://api.example/unsub?token=abc",
        dashboard_url="https://dineadeal.com/dashboard",
        active_deals=12,
    )
    opener = (
        "We noticed Oak <Cafe> isn't promoting specials online yet. "
        "DineADeal can list them for free."
    )
    assert text_body.index(opener) < text_body.index("DineADeal is where diners look")
    assert "no commission" in text_body
    assert html.escape(opener) in html_body
    assert "DineADeal can list them for free." in html_body


def test_no_specials_digest_breaks_down_zone_category_and_region() -> None:
    rows = [
        ("british_isles", "Restaurants, Cafe's & Bistro's", False),
        ("british_isles", "Restaurants, Cafe's & Bistro's", False),
        ("british_isles", "Clubs, Bars & Pubs", True),
        ("us_east", "Restaurants, Cafe's & Bistro's", False),
        ("us_east", "Hotels, Resorts & B&B's", None),
        ("australia", "Restaurants, Cafe's & Bistro's", False),
    ]
    stats = no_specials_breakdown(rows)
    assert stats["no_specials"] == 4
    assert stats["no_specials_pct"] == 66.7
    regions = {
        label: (count, total)
        for label, count, total, _pct in stats["no_specials_by_region"]
    }
    assert regions == {"EU": (2, 3), "NA": (1, 2), "Other": (1, 1)}
    body = format_fishy_digest(
        {
            "week_label": "2026-11-08",
            "net_new_lead_emails": 6,
            "unsubscribed": 0,
            "still_to_email": 4,
            "by_zone": [],
            "by_category": [],
            **stats,
        }
    )
    assert "No specials: 4 (67% of 6 new leads)" in body
    assert "British Isles: 2 (67% of 3)" in body
    assert "Restaurants: 4 (100% of 4)" in body
    assert "No specials by region:" in body
    assert "EU: 2 (67% of 3)" in body
    assert "NA: 1 (50% of 2)" in body
    assert "Other: 1 (100% of 1)" in body


def test_dry_run_prints_counts_and_does_not_send(capsys, monkeypatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("dry run must not send")

    monkeypatch.setattr("app.services.email.send_email", boom)
    monkeypatch.setattr("app.services.ntfy.send_ntfy", boom)

    def fake_zone(zone_id: str, *, dry_run: bool = False) -> dict[str, object]:
        assert zone_id == "british_isles"
        assert dry_run is True
        return {
            "zone": zone_id,
            "ok": True,
            "dry_run": True,
            "candidates": 10,
            "leads_inserted": 4,
            "no_specials": 3,
            "has_specials": 1,
            "specials_unknown": 0,
            "skipped_known": 2,
            "outreach_sends": 0,
            "ntfy": None,
        }

    def fake_report() -> dict[str, object]:
        return {
            "week_label": "2026-11-08",
            "net_new_lead_emails": 4,
            "unsubscribed": 1,
            "still_to_email": 4,
            "no_specials": 3,
            "no_specials_pct": 75.0,
            "by_zone": [("British Isles", 4, 100.0)],
            "by_category": [],
            "no_specials_by_zone": [("British Isles", 3, 4, 75.0)],
            "no_specials_by_category": [],
            "no_specials_by_region": [
                ("EU", 3, 4, 75.0),
                ("NA", 0, 0, 0.0),
                ("Other", 0, 0, 0.0),
            ],
        }

    result = run_fishy_dry_run(
        "british_isles",
        run_zone=fake_zone,
        build_report=fake_report,
    )
    printed = capsys.readouterr().out
    assert result["ntfy"] is None
    assert result["summary"]["outreach_sends"] == 0
    assert "Sending is disabled" in printed
    assert "lead rows only" in printed
    assert "Leads inserted: 4" in printed
    assert "No specials: 3" in printed
    assert "Digest text (not posted):" in printed
    assert "No specials: 3 (75% of 4 new leads)" in printed
    assert "EU: 3 (75% of 4)" in printed
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "fishy_finger_dry_run.py"
    ).read_text(encoding="utf-8")
    assert (
        "docker exec mealdeals-celery-nuc python /app/scripts/fishy_finger_dry_run.py "
        "--zone british_isles"
    ) in script
