"""Scraper offer-URL helpers — landing vs deal/menu deep links."""

from app.scrapers.global_retail import (
    GlobalRetailScraper,
    is_generic_landing_url,
    looks_like_offer_url,
)


def test_homepage_is_generic_landing() -> None:
    assert is_generic_landing_url("https://www.chipotle.com/")
    assert is_generic_landing_url("https://www.chipotle.com")
    assert is_generic_landing_url("https://harbourlightsbarbados.com/home")


def test_offer_and_menu_paths_are_not_generic() -> None:
    assert looks_like_offer_url("https://www.dominos.co.uk/deals")
    assert looks_like_offer_url("https://www.greggs.co.uk/menu")
    assert looks_like_offer_url("https://www.dominos.com/en/pages/order/#!/deals")
    assert not is_generic_landing_url("https://www.kfc.co.uk/offers")
    assert not is_generic_landing_url("https://www.tesco.com/groceries/en-GB/promotions")


async def test_resolve_offer_destination_prefers_live_offers_page(
    monkeypatch,
) -> None:
    scraper = GlobalRetailScraper()

    async def fake_parse(url: str, merchant: str) -> dict:
        if url.rstrip("/").endswith("/offers"):
            return {"offer_snippet": "Happy hour half price", "title": "Offers"}
        if url.rstrip("/") in {"https://www.chipotle.com", "https://www.chipotle.com/"}:
            return {"title": "Chipotle", "website": "https://www.chipotle.com/"}
        return {}

    monkeypatch.setattr(scraper, "_try_live_parse", fake_parse)
    dest, live = await scraper._resolve_offer_destination(
        "https://www.chipotle.com/", "Chipotle"
    )
    assert dest == "https://www.chipotle.com/offers"
    assert "Happy hour" in str(live.get("offer_snippet"))


async def test_resolve_offer_destination_keeps_configured_deep_link(
    monkeypatch,
) -> None:
    scraper = GlobalRetailScraper()

    async def fake_parse(url: str, merchant: str) -> dict:
        return {"title": merchant, "offer_snippet": "2 for 1"}

    monkeypatch.setattr(scraper, "_try_live_parse", fake_parse)
    dest, _live = await scraper._resolve_offer_destination(
        "https://www.dominos.co.uk/deals", "Domino's"
    )
    assert dest == "https://www.dominos.co.uk/deals"
