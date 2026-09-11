"""Affiliate URL cleaning / wrapping unit tests."""

from app.core.config import Settings
from app.services.affiliate import (
    AffiliateNetwork,
    build_affiliate_urls,
    detect_network,
    outbound_destination_url,
    repair_concatenated_url,
    resolve_click_target,
    strip_tracking_params,
    with_scrape_identity,
    wrap_affiliate_url,
)


def test_strip_tracking_params_removes_utm() -> None:
    raw = "https://www.example.com/deal?id=1&utm_source=email&utm_medium=cpc&keep=yes"
    clean = strip_tracking_params(raw)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "keep=yes" in clean
    assert "id=1" in clean


def test_strip_tracking_params_preserves_hash_router_fragment() -> None:
    raw = "https://www.dominos.com/en/pages/order/?utm_source=email#!/deals"
    clean = strip_tracking_params(raw)
    assert clean.endswith("#!/deals")
    assert "utm_source" not in clean


def test_detect_amazon() -> None:
    assert detect_network("https://www.amazon.co.uk/dp/B00TEST") == AffiliateNetwork.AMAZON


def test_wrap_amazon_tag() -> None:
    settings = Settings(amazon_associate_tag="mealdeals-uk-21")
    wrapped = wrap_affiliate_url(
        "https://www.amazon.co.uk/dp/B00TEST?utm_source=x",
        settings=settings,
    )
    assert "tag=mealdeals-uk-21" in wrapped
    assert "utm_source" not in wrapped


def test_wrap_amazon_preserves_fragment() -> None:
    settings = Settings(amazon_associate_tag="mealdeals-uk-21")
    wrapped = wrap_affiliate_url(
        "https://www.amazon.co.uk/dp/B00TEST#!/offer",
        settings=settings,
    )
    assert "tag=mealdeals-uk-21" in wrapped
    assert wrapped.endswith("#!/offer")


def test_build_affiliate_urls_pair() -> None:
    clean, aff = build_affiliate_urls(
        "https://www.booking.com/hotel/gb/test.html?utm_campaign=ads"
    )
    assert "utm_campaign" not in clean
    assert "aid=" in aff


def test_with_scrape_identity_keeps_existing_query_and_fragment() -> None:
    raw = with_scrape_identity(
        "https://www.dominos.com/en/pages/order/#!/deals",
        city="London",
        locality="London",
        country="GB",
    )
    parsed_query_before_hash = raw.split("#")[0]
    assert "city=London" in parsed_query_before_hash
    assert "#!/deals" in raw
    assert raw.count("?") == 1


def test_with_scrape_identity_does_not_double_question_mark() -> None:
    raw = with_scrape_identity(
        "https://www.example.com/offers?promo=lunch",
        city="Galway",
        locality="Galway City",
        country="IE",
    )
    assert "?promo=lunch&" in raw or "promo=lunch" in raw
    assert "??" not in raw
    assert raw.count("?") == 1
    assert "city=Galway" in raw


def test_repair_hash_router_uniqueness_dumped_in_fragment() -> None:
    broken = (
        "https://www.dominos.com/en/pages/order/#!/deals"
        "?city=London&locality=London&country=GB&utm_source=mealdeals_scraper"
    )
    repaired = repair_concatenated_url(broken)
    assert "#!/deals" in repaired
    assert "city=London" in repaired.split("#")[0]
    destination = outbound_destination_url(broken)
    assert destination == "https://www.dominos.com/en/pages/order/#!/deals"


def test_repair_double_question_mark_concat() -> None:
    broken = (
        "https://www.example.com/offers?promo=1"
        "?city=Austin&locality=Austin&country=US&utm_source=mealdeals_scraper"
    )
    destination = outbound_destination_url(broken)
    assert destination == "https://www.example.com/offers?promo=1"
    assert "city=" not in destination


def test_outbound_strips_identity_but_keeps_merchant_query() -> None:
    url = (
        "https://www.tesco.com/groceries/en-GB/promotions"
        "?city=Manchester&locality=Manchester&country=GB&utm_source=mealdeals_scraper"
    )
    destination = outbound_destination_url(url)
    assert destination == "https://www.tesco.com/groceries/en-GB/promotions"


def test_build_affiliate_urls_keeps_identity_on_clean_only() -> None:
    raw = with_scrape_identity(
        "https://www.chipotle.com/",
        city="Austin",
        locality="Austin",
        country="US",
    )
    clean, aff = build_affiliate_urls(raw)
    assert "city=Austin" in clean
    assert "utm_source" not in clean
    assert "city=" not in aff
    assert aff.rstrip("/") == "https://www.chipotle.com"


def test_resolve_click_target_recovers_fragment_from_scraped_raw() -> None:
    scraped = (
        "https://www.dominos.com/en/pages/order/#!/deals"
        "?city=Dublin&locality=Dublin&country=IE&utm_source=mealdeals_scraper"
    )
    # Older ingest dropped the fragment on affiliate_url.
    stale_affiliate = "https://www.dominos.com/en/pages/order/"
    target = resolve_click_target(
        scraped_raw_url=scraped,
        affiliate_url=stale_affiliate,
        clean_url=stale_affiliate,
    )
    assert target == "https://www.dominos.com/en/pages/order/#!/deals"


def test_resolve_click_target_does_not_strip_lone_city_param() -> None:
    """Store-locator ?city= is kept unless it is our city+locality+country triplet."""
    url = "https://www.example.com/stores?city=london"
    target = resolve_click_target(
        scraped_raw_url=url,
        affiliate_url=None,
        clean_url=None,
    )
    assert target == url
