"""Malformed scraped hrefs must be skipped, not raised."""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.scrapers.offer_links import extract_offer_url_from_soup
from app.scrapers.url_safety import safe_urljoin
from app.services.deal_link import classify_deal_url, normalize_outbound_url


def test_safe_urljoin_drops_invalid_ipv6_hrefs() -> None:
    base = "https://example.com/menu"
    assert safe_urljoin(base, "http://[invalid") is None
    assert safe_urljoin(base, "http://[::1") is None
    assert safe_urljoin(base, "//[elementor-template%20id=2073]") is None
    assert safe_urljoin(base, "https://[elementor-template%20id=2073]/foo") is None
    assert safe_urljoin(base, "/deals/lunch-special") == (
        "https://example.com/deals/lunch-special"
    )


def test_normalize_outbound_url_drops_bracketed_junk() -> None:
    assert normalize_outbound_url("http://[invalid") is None
    assert normalize_outbound_url("https://[elementor-template%20id=2073]/foo") is None
    assert (
        normalize_outbound_url("https://example.com/deals/lunch")
        == "https://example.com/deals/lunch"
    )


def test_classify_deal_url_does_not_raise_on_invalid_ipv6() -> None:
    assert classify_deal_url("http://[::1").value == "homepage"


def test_extract_offer_url_skips_bad_hrefs_and_keeps_real_offer() -> None:
    html = """
    <html><body>
      <a href="http://[invalid">broken ipv6</a>
      <a href="//[elementor-template%20id=2073]">elementor template</a>
      <a href="https://[elementor-template%20id=2073]/foo">also broken</a>
      <a href="/deals/lunch-special">Lunch deal 20% off</a>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    found = extract_offer_url_from_soup(soup, page_url="https://bistro.example/menu")
    assert found == "https://bistro.example/deals/lunch-special"
