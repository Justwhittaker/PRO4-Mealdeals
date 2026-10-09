"""Shared deal-quality helper used by the newsletter and later junk cleanup."""

from __future__ import annotations

from app.services.deal_quality import (
    QualityReject,
    filter_kept_in_order,
    promotional_price_label,
    rejection_reason,
)


def test_spam_and_parked_titles_are_rejected() -> None:
    assert (
        rejection_reason(
            title="AKUNBOS: Situs Slot Gacor Hari Ini",
            merchant_name="Cardo's Steakhouse",
            deal_price="10.00",
        )
        is QualityReject.SPAM
    )
    assert (
        rejection_reason(
            title="Parked Domain name on Hostinger",
            merchant_name="Parked Domain",
            deal_price="5",
        )
        is QualityReject.PARKED_DOMAIN
    )


def test_generic_titles_and_venue_only_names_are_rejected() -> None:
    assert (
        rejection_reason(
            title="Hotel Details",
            merchant_name="Aiden",
            deal_price="40",
        )
        is QualityReject.GENERIC_TITLE
    )
    assert (
        rejection_reason(
            title="Overview & Booking",
            merchant_name="Sea Breeze Guest House",
            deal_price="90",
        )
        is QualityReject.GENERIC_TITLE
    )
    assert (
        rejection_reason(
            title="Cardo's Steakhouse",
            merchant_name="Cardo's Steakhouse",
            deal_price="25",
        )
        is QualityReject.GENERIC_TITLE
    )


def test_lodging_without_dining_is_rejected_and_a_carvery_stays() -> None:
    assert (
        rejection_reason(
            title="Deluxe room package",
            merchant_name="Legoland Hotel Dubai",
            venue_category="hotels-resorts-bbs",
            deal_price="200",
        )
        is QualityReject.LODGING_WITHOUT_DINING
    )
    assert (
        rejection_reason(
            title="City view room",
            merchant_name="Doha Dynasty Hotel",
            deal_price="80",
        )
        is QualityReject.LODGING_WITHOUT_DINING
    )
    assert (
        rejection_reason(
            title="Sunday carvery lunch",
            merchant_name="Galway Bay Hotel",
            venue_category="hotels-resorts-bbs",
            description="Carvery lunch in the hotel restaurant.",
            deal_price="16",
        )
        is None
    )


def test_zero_prices_need_a_percent_or_free_item() -> None:
    assert (
        rejection_reason(
            title="Steak night",
            merchant_name="The Skeff",
            deal_price="0.00",
        )
        is QualityReject.PRICE
    )
    assert rejection_reason(title="Lunch deal", merchant_name="Cafe", deal_price=None) is (
        QualityReject.PRICE
    )
    assert (
        rejection_reason(
            title="20% off fish and chips",
            merchant_name="McDonagh's",
            deal_price="0.00",
        )
        is None
    )
    assert promotional_price_label("20% off fish and chips", "") == "20% off"
    assert (
        rejection_reason(
            title="Free kids ice cream with any main",
            merchant_name="Murphy's Ice Cream",
            deal_price=0,
        )
        is None
    )
    assert promotional_price_label("Free kids ice cream with any main", "") == "Free"


def test_filter_helper_drops_spam_and_keeps_the_first_duplicate() -> None:
    rows = [
        {
            "title": "AKUNBOS: Situs Slot Gacor",
            "merchant": "Cardo's Steakhouse",
            "price": "10",
        },
        {"title": "Early-bird set menu", "merchant": "Ard Bia", "price": "22"},
        {"title": "Early-bird set menu", "merchant": "Ard Bia", "price": "22"},
        {
            "title": "Parked Domain name on Hostinger",
            "merchant": "Hostinger",
            "price": "1",
        },
    ]
    kept = filter_kept_in_order(
        rows,
        title=lambda row: row["title"],
        merchant_name=lambda row: row["merchant"],
        deal_price=lambda row: row["price"],
    )
    assert [row["merchant"] for row in kept] == ["Ard Bia"]
