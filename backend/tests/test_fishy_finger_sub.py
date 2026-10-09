"""Fishy Finger Sub: chains, email quality, outreach order, digest, schedule."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

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
from app.services.fishy_finger.schedule import (
    DUBLIN,
    FISHY_DIGEST_HOUR,
    FISHY_DIGEST_MINUTE,
    EuropeDublinWeekly,
    fishy_week_start,
    fishy_zone_clock,
    next_dublin_sunday_after,
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


def test_fishy_quality_does_not_reorder_the_existing_queue() -> None:
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    fishy_old = _contact(
        source_segment=FISHY_FINGER_SEGMENT,
        email="owner@old.example",
        email_quality_score=96,
        last_outreach_sent_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    regular = _contact(email="info@new.example", email_quality_score=1)
    batch = rank_outreach_candidates(
        [fishy_old, regular],
        now=now,
        min_days=28,
        max_rows=95,
    )
    assert [row.email for row in batch] == ["info@new.example", "owner@old.example"]


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
    assert ZONE_CYCLE_BASE_HOURS == (6, 18)
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

    clocks = [fishy_zone_clock(zone_id) for zone_id in ZONE_ORDER]
    assert clocks[0] == (8, 0)
    assert clocks[1] == (8, ZONE_BEAT_STAGGER_MINUTES)
    minutes = [hour * 60 + minute for hour, minute in clocks]
    assert minutes == sorted(minutes)
    assert minutes[-1] - minutes[0] == (len(ZONE_ORDER) - 1) * ZONE_BEAT_STAGGER_MINUTES

    for zone_id in ZONE_ORDER:
        fishy = celery_app.conf.beat_schedule[f"fishy-finger-{zone_id}"]
        deal = celery_app.conf.beat_schedule[f"scrape-zone-{zone_id}"]
        assert fishy["task"] == "app.workers.tasks.scrape_fishy_finger_zone"
        assert fishy["kwargs"] == {"zone_id": zone_id}
        assert isinstance(fishy["schedule"], EuropeDublinWeekly)
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
    )
    session = _Session()
    row = insert_fishy_lead(session, lead)  # type: ignore[arg-type]
    assert session.added == [row]
    assert row.source_segment == FISHY_FINGER_SEGMENT
    assert row.lead_zone == "british_isles"
    assert row.email_quality_score == 96
    assert row.country_code == "IE"
    assert row.city == "Galway"
    assert lead_is_known(lead, {("email", "owner@oak.example")})
    assert not lead_is_known(lead, set())


def test_migration_adds_fishy_columns() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "016_fishy_finger_sub.py"
    )
    text = path.read_text(encoding="utf-8")
    assert 'revision: str = "016_fishy_finger"' in text
    assert 'down_revision: Union[str, None] = "015_marketing_outreach"' in text
    assert "source_segment" in text
    assert "lead_zone" in text
    assert "email_quality_score" in text
