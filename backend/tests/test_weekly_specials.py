"""Galway Weekly Specials stay in Ireland, drop junk, and link to dineadeal.com."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pathlib import Path

from app.models.newsletter import NewsletterSubscriber
from app.scrapers.source_filters import is_chain_name
from app.services.click_referral import clean_utm
from app.services.listing_quality import (
    collapse_repeated_kind_words,
    compose_offer_title,
    is_generated_template_title,
)
from app.services.newsletter import assign_resolved_location
from app.services.weekly_specials import (
    WeeklyDeal,
    backfill_subscriber_location,
    country_deals_statement,
    deal_public_url,
    display_price,
    format_money,
    render_weekly_issue,
    resolve_subscriber_place,
    review_candidates,
    send_weekly_special_to_subscriber,
)
from app.services.weekly_specials_fixtures import galway_issue_fixtures

_UTM = "utm_source=newsletter&utm_medium=email&utm_campaign=weekly_specials"


def _justin(location: str = "Galway", country: str | None = "IE", city: str | None = "Galway"):
    return NewsletterSubscriber(
        name="Justin",
        surname="Whittaker",
        email="justin@example.com",
        location=location,
        country_code=country,
        city=city,
        is_subscribed=True,
        unsubscribe_token="preview-token-not-sent",
    )


def test_galway_issue_is_irish_with_galway_first() -> None:
    subscriber = _justin()
    subject, text, html, selection, excluded = render_weekly_issue(
        subscriber,
        galway_issue_fixtures(),
    )
    assert selection.scope == "country"
    assert subject == "Dine A Deal — this week's specials in Galway"
    assert "including a few from elsewhere in Ireland" in text
    countries = {deal.country_code for deal in selection.deals}
    assert countries == {"IE"}
    cities = [deal.city for deal in selection.deals]
    assert cities[0] == "Galway"
    assert cities.index("Galway") < cities.index("Limerick")
    assert cities.index("Limerick") < cities.index("Cork")
    assert cities.index("Cork") < cities.index("Dublin")
    galway_count = cities.count("Galway")
    assert galway_count >= 1
    assert all(city == "Galway" for city in cities[:galway_count])

    reasons = {reason for _deal, reason in excluded}
    assert "spam" in reasons
    assert "parked_domain" in reasons
    assert "generic_title" in reasons
    assert "lodging_without_dining" in reasons
    assert "price" in reasons
    assert "duplicate" in reasons
    assert "other_country" in reasons

    for needle in (
        "AKUNBOS",
        "Gacor",
        "Hostinger",
        "Hotel Details",
        "Deluxe room package",
        "Legoland",
        "Doha Dynasty",
        "Seoul",
        "Warsaw",
        "Auckland",
        "Cape Town",
        "Sydney",
        "FJD",
        "KRW",
        "GYD",
        "QAR",
        "0.00",
        "slot-spam.example",
        "ardbia.example",
        "legoland-hotel.example",
    ):
        assert needle not in text
        assert needle not in html

    assert "Ard Bia" in text
    assert "Galway Bay Hotel" in text
    assert "The Locke" in text
    assert "Farmgate Cafe" in text
    assert text.count("Weekday lunch special") == 1
    kai = next(deal for deal in selection.deals if deal.merchant_name == "Kai Cafe")
    assert kai.city == "Galway"
    assert "€22.00" in text
    assert "€14.50" in text
    assert "€11.04" in text
    assert "20% off" in text
    assert "Free" in text
    assert "USD" not in text


def test_deal_links_are_dineadeal_pages_with_utm() -> None:
    _subject, text, html, selection, _excluded = render_weekly_issue(
        _justin(),
        galway_issue_fixtures(),
    )
    assert selection.deals
    for deal in selection.deals:
        href = deal_public_url(deal)
        assert href.startswith("https://dineadeal.com/")
        assert "/deals/" in href
        assert href.endswith(f"?{_UTM}")
        assert href in text
        assert href.replace("&", "&amp;") in html
        if deal.outbound_url:
            assert deal.outbound_url not in text
            assert deal.outbound_url not in html
    galway = next(deal for deal in selection.deals if deal.city == "Galway")
    assert f"https://dineadeal.com/ie/galway/deals/{galway.id}?{_UTM}" in text


def test_empty_local_fallback_does_not_pad_with_other_countries() -> None:
    foreign = [
        deal
        for deal in galway_issue_fixtures()
        if deal.country_code != "IE"
    ]
    _subject, text, html, selection, excluded = render_weekly_issue(
        _justin(),
        foreign,
    )
    assert selection.deals == []
    assert selection.scope == "none"
    assert "No new local deals this week in Galway" in text
    assert "No new local deals this week in Galway" in html
    assert "<ul" not in html
    assert all(reason == "other_country" for _deal, reason in excluded)
    for needle in ("Seoul", "Dubai", "Legoland", "Warsaw", "Sydney", "FJD", "KRW"):
        assert needle not in text


def test_location_string_galway_resolves_to_ireland() -> None:
    place = resolve_subscriber_place(None, None, "Galway")
    assert place.country_code == "IE"
    assert place.city == "Galway"
    selection, _excluded = review_candidates(galway_issue_fixtures(), place)
    assert {deal.country_code for deal in selection.deals} == {"IE"}
    assert selection.deals[0].city == "Galway"

    spelled = resolve_subscriber_place(None, None, "Galway, Ireland")
    assert spelled.country_code == "IE"
    assert spelled.city == "Galway"
    coded = resolve_subscriber_place(None, None, "Galway, IE")
    assert coded.country_code == "IE"
    assert coded.city == "Galway"


def test_ambiguous_city_without_a_country_is_not_filled_from_abroad() -> None:
    place = resolve_subscriber_place(None, None, "London")
    assert place.country_code is None
    deals = galway_issue_fixtures()
    selection, excluded = review_candidates(deals, place)
    assert selection.deals == []
    assert all(reason == "unknown_place" for _deal, reason in excluded)

    london = resolve_subscriber_place(None, None, "London, UK")
    assert london.country_code == "GB"
    assert london.city == "London"


def test_fewer_local_deals_are_sent_without_padding() -> None:
    only_galway = [
        deal
        for deal in galway_issue_fixtures()
        if deal.merchant_name == "Ard Bia"
    ]
    place = resolve_subscriber_place("IE", "Galway", "Galway")
    selection, _excluded = review_candidates(only_galway, place)
    assert [deal.merchant_name for deal in selection.deals] == ["Ard Bia"]
    assert selection.scope == "city"


def test_format_money_uses_symbol_and_zero_decimal_currencies() -> None:
    assert format_money(Decimal("22"), "EUR") == "€22.00"
    assert format_money(Decimal("15000"), "KRW") == "₩15,000"


def test_prices_use_the_subscriber_currency() -> None:
    burger = next(
        deal for deal in galway_issue_fixtures() if deal.merchant_name == "The Quays Bar"
    )
    assert burger.currency_code == "USD"
    assert burger.deal_price == Decimal("12.00")
    assert display_price(burger, "EUR") == "€11.04"


def test_country_query_never_selects_a_global_feed() -> None:
    statement = country_deals_statement("IE", city="Galway", limit=80)
    sql = str(statement.compile(compile_kwargs={"literal_binds": False}))
    assert "country_code" in sql
    assert "is_active" in sql
    params = list(statement.compile().params.values())
    assert "IE" in params
    assert "galway" in params


def _us_deal(
    deal_id: str,
    merchant: str,
    city: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    when: datetime | None = None,
) -> WeeklyDeal:
    return WeeklyDeal(
        id=deal_id,
        title=f"Lunch at {merchant}",
        description="Weekday lunch",
        merchant_name=merchant,
        venue_category="restaurants-cafes-bistros",
        country_code="US",
        city=city,
        latitude=lat,
        longitude=lon,
        deal_price=Decimal("12.00"),
        currency_code="USD",
        created_at=when or datetime(2026, 10, 1, tzinfo=timezone.utc),
        outbound_url="https://merchant.example/menu",
    )


def test_utah_stops_at_the_state_when_any_utah_deal_qualifies() -> None:
    place = resolve_subscriber_place("US", "Salt Lake City", "Salt Lake City, Utah")
    assert place.country_code == "US"
    assert place.city == "Salt Lake City"
    assert place.region_code == "UT"
    assert place.region_label == "Utah"

    deals = [
        _us_deal(
            "30000000-0000-4000-8000-000000000001",
            "Red Iguana",
            "Salt Lake City",
            lat=40.7608,
            lon=-111.8910,
            when=datetime(2026, 10, 1, tzinfo=timezone.utc),
        ),
        _us_deal(
            "30000000-0000-4000-8000-000000000002",
            "Communal",
            "Provo",
            lat=40.2338,
            lon=-111.6585,
            when=datetime(2026, 10, 2, tzinfo=timezone.utc),
        ),
        _us_deal(
            "30000000-0000-4000-8000-000000000003",
            "Painted Pony",
            "St George",
            lat=37.0965,
            lon=-113.5684,
            when=datetime(2026, 10, 3, tzinfo=timezone.utc),
        ),
        _us_deal(
            "30000000-0000-4000-8000-000000000004",
            "Trestle",
            "Evanston",
            lat=41.2683,
            lon=-110.9632,
            when=datetime(2026, 10, 4, tzinfo=timezone.utc),
        ),
        _us_deal(
            "30000000-0000-4000-8000-000000000005",
            "Root Down",
            "Denver",
        ),
        _us_deal(
            "30000000-0000-4000-8000-000000000006",
            "Joe's Pizza",
            "New York",
        ),
    ]
    selection, excluded = review_candidates(deals, place)
    assert [deal.city for deal in selection.deals] == [
        "Salt Lake City",
        "Provo",
        "Evanston",
        "St George",
    ]
    assert selection.scope == "region"
    reasons = {deal.city: reason for deal, reason in excluded}
    assert reasons["Denver"] == "other_region"
    assert reasons["New York"] == "other_region"
    _subject, text, _html, _selection, _excluded = render_weekly_issue(
        _justin(location="Salt Lake City, Utah", country="US", city="Salt Lake City"),
        deals,
    )
    assert "and the rest of Utah" in text
    assert "Denver" not in text
    assert "New York" not in text


def test_utah_with_one_local_deal_does_not_pad_the_rest_of_the_us() -> None:
    place = resolve_subscriber_place(None, None, "Salt Lake City, UT")
    assert place.country_code == "US"
    assert place.region_code == "UT"
    deals = [
        _us_deal("30000000-0000-4000-8000-000000000011", "Red Iguana", "Salt Lake City"),
        _us_deal("30000000-0000-4000-8000-000000000012", "Root Down", "Denver"),
    ]
    selection, excluded = review_candidates(deals, place)
    assert [deal.city for deal in selection.deals] == ["Salt Lake City"]
    assert selection.scope == "city"
    assert excluded[0][1] == "other_region"


def test_utah_falls_back_to_the_country_only_when_the_state_is_empty() -> None:
    place = resolve_subscriber_place("US", "Salt Lake City", "Salt Lake City, UT")
    deals = [
        _us_deal("30000000-0000-4000-8000-000000000021", "Root Down", "Denver"),
        _us_deal("30000000-0000-4000-8000-000000000022", "Joe's Pizza", "New York"),
    ]
    selection, excluded = review_candidates(deals, place)
    assert {deal.city for deal in selection.deals} == {"Denver", "New York"}
    assert selection.scope == "country"
    assert excluded == []
    assert "elsewhere in the US" in render_weekly_issue(
        _justin(location="Salt Lake City, UT", country="US", city="Salt Lake City"),
        deals,
    )[1]


def test_los_angeles_ca_is_california_not_canada() -> None:
    place = resolve_subscriber_place(None, None, "Los Angeles, CA")
    assert place.country_code == "US"
    assert place.city == "Los Angeles"
    assert place.region_code == "CA"
    vancouver = resolve_subscriber_place(None, None, "Vancouver, CA")
    assert vancouver.country_code == "CA"
    assert vancouver.city == "Vancouver"
    assert vancouver.region_code == "BC"


def test_galway_has_no_state_tier() -> None:
    place = resolve_subscriber_place(None, None, "Galway, IE")
    assert place.region_code is None
    assert place.country_code == "IE"


def test_backfill_fills_null_city_and_state_without_overwriting() -> None:
    subscriber = _justin(location="Salt Lake City, Utah", country=None, city=None)
    subscriber.region = None
    assert backfill_subscriber_location(subscriber) is True
    assert subscriber.country_code == "us"
    assert subscriber.city == "Salt Lake City"
    assert subscriber.region == "UT"

    subscriber.city = "Provo"
    subscriber.region = None
    assert backfill_subscriber_location(subscriber) is True
    assert subscriber.city == "Provo"
    assert subscriber.region == "UT"

    subscriber.region = "CO"
    assert backfill_subscriber_location(subscriber) is False
    assert subscriber.region == "CO"
    assert subscriber.city == "Provo"


def test_signup_capture_uses_geolocation_and_typed_text() -> None:
    subscriber = _justin(location="ignored", country=None, city=None)
    assign_resolved_location(
        subscriber,
        location="Salt Lake City, Utah",
        country_code="US",
        city="Salt Lake City",
        region="UT",
    )
    assert subscriber.country_code == "us"
    assert subscriber.city == "Salt Lake City"
    assert subscriber.region == "UT"

    assign_resolved_location(
        subscriber,
        location="Los Angeles, CA",
        country_code=None,
        city=None,
        region=None,
    )
    assert subscriber.country_code == "us"
    assert subscriber.city == "Los Angeles"
    assert subscriber.region == "CA"

    assign_resolved_location(
        subscriber,
        location="Park City, UT",
        country_code="US",
        city="Park City",
        region="UT",
    )
    assert subscriber.city == "Park City"
    assert subscriber.region == "UT"
    assert subscriber.country_code == "us"


def test_click_referral_tags_reject_urls() -> None:
    assert clean_utm("newsletter") == "newsletter"
    assert clean_utm("weekly_specials") == "weekly_specials"
    assert clean_utm(" https://evil.example ") is None
    assert clean_utm("") is None
    assert clean_utm("a" * 65) is None


def _ie_deal(
    deal_id: str,
    merchant: str,
    city: str,
    title: str,
    *,
    price: str = "14.00",
    description: str = "Weekday lunch",
    lat: float | None = None,
    lon: float | None = None,
    when: datetime | None = None,
) -> WeeklyDeal:
    return WeeklyDeal(
        id=deal_id,
        title=title,
        description=description,
        merchant_name=merchant,
        venue_category="restaurants-cafes-bistros",
        country_code="IE",
        city=city,
        latitude=lat,
        longitude=lon,
        deal_price=Decimal(price) if price else None,
        currency_code="EUR",
        created_at=when or datetime(2026, 10, 2, tzinfo=timezone.utc),
        outbound_url="https://merchant.example/menu",
    )


def _galway_chain_issue() -> list[WeeklyDeal]:
    """The live Galway pattern: four chain templates copied across nearby towns."""
    chains = (
        ("Subway Takeaway", "Subway Takeaway Takeaway Deal — {city}"),
        ("Apache Pizza Takeaway", "Apache Pizza Takeaway Takeaway Deal — {city}"),
        ("Supermac's Takeaway", "Supermac's Takeaway Takeaway Deal — {city}"),
        ("Papa John's Takeaway", "Papa John's Takeaway Takeaway Deal — {city}"),
    )
    towns = (
        ("Galway", 53.2707, -9.0568),
        ("Westport", 53.8009, -9.5227),
        ("Limerick", 52.6638, -8.6267),
    )
    rows: list[WeeklyDeal] = [
        _ie_deal(
            "40000000-0000-4000-8000-000000000001",
            "Ard Bia",
            "Galway",
            "Early-bird set menu",
            price="22.00",
            lat=53.2707,
            lon=-9.0568,
            when=datetime(2026, 10, 3, tzinfo=timezone.utc),
        ),
        _ie_deal(
            "40000000-0000-4000-8000-000000000002",
            "Kai Cafe",
            "Galway",
            "Weekday lunch special",
            price="14.50",
            lat=53.2710,
            lon=-9.0570,
            when=datetime(2026, 10, 4, tzinfo=timezone.utc),
        ),
    ]
    number = 10
    for merchant, title_tmpl in chains:
        for city, lat, lon in towns:
            number += 1
            rows.append(
                _ie_deal(
                    f"40000000-0000-4000-8000-{number:012d}",
                    merchant,
                    city,
                    title_tmpl.format(city=city),
                    price="0",
                    description=(
                        "Chain takeaway promotion — often buy-one-get-one-free, "
                        "meal deals, or limited-time pizza offers."
                    ),
                    lat=lat,
                    lon=lon,
                    when=datetime(2026, 10, 5, tzinfo=timezone.utc),
                )
            )
    return rows


def test_independents_rank_above_chain_templates_and_merchants_are_unique() -> None:
    place = resolve_subscriber_place("IE", "Galway", "Galway")
    deals = _galway_chain_issue()
    selection, excluded = review_candidates(deals, place)
    names = [deal.merchant_name for deal in selection.deals]
    assert names[:2] == ["Kai Cafe", "Ard Bia"]
    assert all(not is_chain_name(name) for name in names[:2])
    chain_names = names[2:]
    assert chain_names == [
        "Subway Takeaway",
        "Apache Pizza Takeaway",
        "Supermac's Takeaway",
        "Papa John's Takeaway",
    ]
    assert all(deal.city == "Galway" for deal in selection.deals if is_chain_name(deal.merchant_name))
    assert len(names) == len(set(names))
    reasons = {(deal.merchant_name, deal.city): reason for deal, reason in excluded}
    assert reasons[("Subway Takeaway", "Westport")] == "duplicate_merchant"
    assert reasons[("Apache Pizza Takeaway", "Limerick")] == "duplicate_merchant"

    short, short_excluded = review_candidates(deals, place, limit=2)
    assert [deal.merchant_name for deal in short.deals] == ["Kai Cafe", "Ard Bia"]
    assert any(
        is_chain_name(deal.merchant_name) and reason == "over_limit"
        for deal, reason in short_excluded
    )


def test_titles_drop_repeated_kind_words_and_blank_prices_are_offers() -> None:
    assert compose_offer_title(
        "Apache Pizza Takeaway", "Takeaway Deal", "Galway"
    ) == "Apache Pizza Takeaway Deal — Galway"
    assert compose_offer_title(
        "Pizza Pizza Takeaway", "Takeaway Deal", "Toronto"
    ) == "Pizza Pizza Takeaway Deal — Toronto"
    assert (
        collapse_repeated_kind_words("Apache Pizza Takeaway Takeaway Deal — Galway")
        == "Apache Pizza Takeaway Deal — Galway"
    )
    assert is_generated_template_title("Apache Pizza Takeaway Deal — Galway")
    assert is_generated_template_title("Happy hour pints") is False

    place = resolve_subscriber_place("IE", "Galway", "Galway")
    deals = _galway_chain_issue()
    _subject, text, html, selection, _excluded = render_weekly_issue(_justin(), deals)
    apache = next(deal for deal in selection.deals if "Apache" in deal.merchant_name)
    assert "Takeaway Takeaway" not in text
    assert "Takeaway Takeaway" not in html
    assert "Apache Pizza Takeaway Deal — Galway" in text
    assert display_price(apache, "EUR") == "Buy one, get one free"
    assert "Buy one, get one free" in text
    bare = _ie_deal(
        "40000000-0000-4000-8000-000000000099",
        "Murphy's Ice Cream",
        "Galway",
        "Free",
        price="0",
        description="",
    )
    assert display_price(bare, "EUR") == "Free with a purchase"


def test_test_send_does_not_update_last_emailed_at(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.weekly_specials.send_email",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        "app.services.weekly_specials.fetch_weekly_deals",
        lambda _session, _place: [],
    )

    class Session:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

    session = Session()
    subscriber = _justin()
    subscriber.is_subscribed = False
    subscriber.last_emailed_at = None
    result = send_weekly_special_to_subscriber(
        session,
        subscriber,
        record_send=False,
        allow_unsubscribed=True,
    )
    assert result["sent"] is True
    assert subscriber.last_emailed_at is None
    assert session.committed is False
    assert session.rolled_back is True


def test_workflow_test_email_is_opt_in_and_the_schedule_is_unchanged() -> None:
    workflow = Path(__file__).resolve().parents[2] / ".github/workflows/weekly-specials.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "cron: \"0 9 * * 5\"" in text
    assert "test_email:" in text
    assert "WEEKLY_TEST_EMAIL" in text
    assert 'python scripts/send_weekly_specials.py --test-email "$WEEKLY_TEST_EMAIL"' in text
    assert "python scripts/send_weekly_specials.py\n" in text
    script = Path(__file__).resolve().parents[1] / "scripts/send_weekly_specials.py"
    script_text = script.read_text(encoding="utf-8")
    assert "--test-email" in script_text
    assert "last_emailed_at" in script_text
