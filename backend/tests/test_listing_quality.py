"""AdSense-facing listing copy: block spam, rewrite homepage titles, drop fake discounts."""

from __future__ import annotations

from decimal import Decimal

from app.services.listing_quality import (
    is_low_value_title,
    is_policy_violation,
    prepare_public_listing,
    public_original_price,
)


def test_policy_blocks_gambling_page_titles() -> None:
    assert is_policy_violation(
        "House of Bing: Demo Pragmatic Play Slot Gratis Bonus Akun Demo PG Soft"
    )
    assert is_policy_violation(
        "Shipley's Donuts: MEGA38 - Bandar Game Online Resmi Terbukti Membayar"
    )
    prepared = prepare_public_listing(
        title="House of Bing: Demo Pragmatic Play Slot Gratis",
        description="Bonus akun demo",
        merchant="House of Bing",
        city="Chicago",
        venue_category="restaurants-cafes-bistros",
        is_subscriber=False,
        deal_price=Decimal("3.88"),
        original_price=Decimal("33.38"),
    )
    assert prepared["blocked"] is True


def test_homepage_and_investor_titles_are_rewritten() -> None:
    assert is_low_value_title(
        "Domino's Pizza Takeaway: Domino's Home Page - Domino's Pizza",
        "Domino's Pizza Takeaway",
    )
    assert is_low_value_title(
        "Wingstop Takeaway: Wingstop Restaurants Inc. Investor Relations – NASDAQ: WING",
        "Wingstop Takeaway",
    )
    assert is_low_value_title(
        "Starbucks Coffee: Starbucks®",
        "Starbucks Coffee",
    )
    assert is_low_value_title(
        "Papa John's Takeaway: Papa John’s Pizza Restaurants | Pizza Delivery Ireland",
        "Papa John's Takeaway",
    )
    prepared = prepare_public_listing(
        title="Domino's Pizza Takeaway: Domino's Home Page - Domino's Pizza",
        description="Order pizza online for delivery",
        merchant="Domino's Pizza Takeaway",
        city="Phoenix",
        venue_category="food-trucks-takeaways",
        is_subscriber=False,
        deal_price=Decimal("8.25"),
        original_price=Decimal("14.00"),
    )
    assert prepared["blocked"] is False
    assert prepared["title"] == "Domino's Pizza Takeaway Deal — Phoenix"
    assert "Takeaway Takeaway" not in str(prepared["title"])
    assert "Home Page" not in str(prepared["title"])
    assert "scraped" not in str(prepared["description"]).lower()
    assert prepared["original_price"] == Decimal("8.25")


def test_publisher_offer_titles_stay() -> None:
    title = "Olive Garden Restaurant Breakfast Bundle — Philadelphia"
    assert is_low_value_title(title, "Olive Garden Restaurant") is False
    prepared = prepare_public_listing(
        title=title,
        description="Breakfast meal deal for Philadelphia.",
        merchant="Olive Garden Restaurant",
        city="Philadelphia",
        venue_category="restaurants-cafes-bistros",
        is_subscriber=False,
        deal_price=Decimal("0"),
        original_price=Decimal("0"),
    )
    assert prepared["title"] == title


def test_fake_was_price_is_hidden_without_comparison_copy() -> None:
    assert public_original_price(
        Decimal("1.25"),
        Decimal("16"),
        "Best bar burgers in Phoenix",
        trust=False,
    ) == Decimal("1.25")
    assert public_original_price(
        Decimal("9.99"),
        Decimal("14.95"),
        "Save 33% on the lunch set",
        trust=False,
    ) == Decimal("14.95")


def test_subscriber_copy_is_kept() -> None:
    prepared = prepare_public_listing(
        title="Tuesday pasta night",
        description="House-made pasta, written by the restaurant.",
        merchant="Court Street",
        city="New York",
        venue_category="restaurants-cafes-bistros",
        is_subscriber=True,
        deal_price=Decimal("18"),
        original_price=Decimal("24"),
    )
    assert prepared["blocked"] is False
    assert prepared["title"] == "Tuesday pasta night"
    assert prepared["original_price"] == Decimal("24")
