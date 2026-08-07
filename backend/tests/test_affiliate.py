"""Affiliate URL cleaning / wrapping unit tests."""

from app.core.config import Settings
from app.services.affiliate import (
    AffiliateNetwork,
    build_affiliate_urls,
    detect_network,
    strip_tracking_params,
    wrap_affiliate_url,
)


def test_strip_tracking_params_removes_utm() -> None:
    raw = "https://www.example.com/deal?id=1&utm_source=email&utm_medium=cpc&keep=yes"
    clean = strip_tracking_params(raw)
    assert "utm_source" not in clean
    assert "utm_medium" not in clean
    assert "keep=yes" in clean
    assert "id=1" in clean


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


def test_build_affiliate_urls_pair() -> None:
    clean, aff = build_affiliate_urls(
        "https://www.booking.com/hotel/gb/test.html?utm_campaign=ads"
    )
    assert "utm_campaign" not in clean
    assert "aid=" in aff
