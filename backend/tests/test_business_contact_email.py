"""Unit tests for venue email extraction used by marketing_contacts scrape."""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.scrapers.global_retail import GlobalRetailScraper


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_normalize_email_rejects_junk() -> None:
    assert GlobalRetailScraper._normalize_email_candidate("noreply@example.com") is None
    assert GlobalRetailScraper._normalize_email_candidate("foo.png@cdn.com") is None
    assert (
        GlobalRetailScraper._normalize_email_candidate("mailto:hello@venue.com?subject=Hi")
        == "hello@venue.com"
    )
    assert (
        GlobalRetailScraper._normalize_email_candidate("bookings[at]pub.co.uk")
        == "bookings@pub.co.uk"
    )


def test_extract_email_from_mailto_and_jsonld_graph() -> None:
    scraper = GlobalRetailScraper()
    html = """
    <html><body>
      <script type="application/ld+json">
      {
        "@graph": [{
          "@type": "Restaurant",
          "name": "Test Bistro",
          "contactPoint": {"@type": "ContactPoint", "email": "hello@testbistro.example"}
        }]
      }
      </script>
      <footer><a href="mailto:noreply@example.com">x</a></footer>
    </body></html>
    """
    out = scraper._extract_business_contact(
        _soup(html),
        page_url="https://testbistro.example/offers",
        merchant="Test Bistro",
        description=None,
    )
    assert out["email"] == "hello@testbistro.example"
    assert out["business_name"] == "Test Bistro"


def test_extract_email_prefers_footer_mailto() -> None:
    scraper = GlobalRetailScraper()
    html = """
    <html><body>
      <p>Ignore tracking@wixpress.com in body noise</p>
      <footer>
        <a href="mailto:info@goodpub.example">Email us</a>
      </footer>
    </body></html>
    """
    out = scraper._extract_business_contact(
        _soup(html),
        page_url="https://goodpub.example/deals",
        merchant="Good Pub",
        description=None,
    )
    assert out["email"] == "info@goodpub.example"
