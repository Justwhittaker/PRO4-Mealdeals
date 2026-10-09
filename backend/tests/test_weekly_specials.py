"""Galway Weekly Specials stay in Ireland, drop junk, and link to dineadeal.com."""

from __future__ import annotations

from decimal import Decimal

from app.models.newsletter import NewsletterSubscriber
from app.services.click_referral import clean_utm
from app.services.weekly_specials import (
    country_deals_statement,
    deal_public_url,
    display_price,
    format_money,
    render_weekly_issue,
    resolve_subscriber_place,
    review_candidates,
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


def test_click_referral_tags_reject_urls() -> None:
    assert clean_utm("newsletter") == "newsletter"
    assert clean_utm("weekly_specials") == "weekly_specials"
    assert clean_utm(" https://evil.example ") is None
    assert clean_utm("") is None
    assert clean_utm("a" * 65) is None
