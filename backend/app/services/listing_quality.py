"""Public listing quality for AdSense and readers.

Scraped pages sometimes contribute a homepage <title>, an investor-relations
URL, or an unrelated spam page. Those must not appear as dining offers.
Subscriber-written deals are kept as submitted unless they trip a policy block.
"""

from __future__ import annotations

import re
from decimal import Decimal

# Phrases that show up when a venue URL resolves to spam, not a dining offer.
_POLICY_RE = re.compile(
    r"(?i)("
    r"pragmatic\s*play|"
    r"\bpg\s*soft\b|"
    r"akun\s*demo|"
    r"bandar\s+game|"
    r"slot\s+gratis|"
    r"game\s+online\s+resmi|"
    r"terbukti\s+membayar|"
    r"online\s+casino|"
    r"\bsportsbook\b|"
    r"\bporn\b|"
    r"\bxxx\b|"
    r"\bviagra\b|"
    r"\bcialis\b|"
    r"\bmega\d{2,}\b"
    r")"
)

# Site chrome copied from a homepage or corporate page, not an offer.
_CHROME_RE = re.compile(
    r"(?i)("
    r"\bhome\s*page\b|"
    r"\bofficial\s+(?:site|website)\b|"
    r"investor\s+relations|"
    r"\bnasdaq\b|"
    r"\bmaintenance\b|"
    r"store\s+locator|"
    r"order\s+(?:pizza\s+)?online|"
    r"\bfind\s+a\s+store\b|"
    r"\bcoming\s+soon\b|"
    r"pizza\s+delivery\s+ireland"
    r")"
)

_OFFER_RE = re.compile(
    r"(?i)("
    r"meal\s+deal|"
    r"\blunch\b|"
    r"breakfast\s+bundle|"
    r"happy\s+hour|"
    r"drink\s+special|"
    r"\bbogo\b|"
    r"buy\s+one|"
    r"\d+\s*%\s*off|"
    r"\boffers?\b|"
    r"\bspecials?\b|"
    r"\bpromo|"
    r"early[- ]bird|"
    r"set\s+menu|"
    r"spend\s*(?:&|and)\s*save|"
    r"shop\s+discount|"
    r"takeaway\s+deal|"
    r"half[- ]price|"
    r"hot\s+meal|"
    r"\bbundle\b|"
    r"\bdeals?\b"
    r")"
)

_COMPARISON_RE = re.compile(
    r"(?i)("
    r"\d+\s*%\s*off|"
    r"\bwas\s+[$£€]?\s?\d|"
    r"\bhalf[- ]price\b|"
    r"\bsave\s+[$£€]?\s?\d"
    r")"
)

_LABEL_TO_ID: dict[str, str] = {
    "Restaurants, Cafe's & Bistro's": "restaurants-cafes-bistros",
    "Food Trucks & Takeaway's": "food-trucks-takeaways",
    "Wine Farms & Entertainment Venues": "wine-farms-entertainment",
    "Deli's and Grocers": "delis-grocers",
    "Clubs, Bars & Pubs": "clubs-bars-pubs",
    "Hotels, Resorts & B&B's": "hotels-resorts-bbs",
}


def _category_id(value: str | None) -> str:
    raw = (value or "").strip()
    if raw in _PUBLISHER_COPY:
        return raw
    return _LABEL_TO_ID.get(raw, "restaurants-cafes-bistros")


_PUBLISHER_COPY: dict[str, tuple[str, str]] = {
    "restaurants-cafes-bistros": (
        "{merchant} Lunch Meal Deal — {city}",
        "Lunch offer at {merchant} in {city}: a set meal, early-bird, or weekday special. "
        "Confirm today's price and what is included with the venue before you visit.",
    ),
    "food-trucks-takeaways": (
        "{merchant} Takeaway Deal — {city}",
        "Takeaway offer at {merchant} in {city}, such as a meal deal or limited-time menu promotion. "
        "Confirm the current offer with the store before you order.",
    ),
    "wine-farms-entertainment": (
        "{merchant} Tasting & Dining Offer — {city}",
        "Tasting or dining offer at {merchant} in {city}. "
        "Hours and inclusions change, so confirm the current promotion with the venue.",
    ),
    "delis-grocers": (
        "{merchant} Spend & Save — {city}",
        "Grocery offer at {merchant} in {city}, such as money off a shop when you spend a set amount. "
        "Confirm the current threshold on the store's offers page.",
    ),
    "clubs-bars-pubs": (
        "{merchant} Happy Hour — {city}",
        "Drink special at {merchant} in {city}. "
        "Happy-hour times and included drinks change, so confirm them with the venue before you go.",
    ),
    "hotels-resorts-bbs": (
        "{merchant} Hotel Dining Offer — {city}",
        "Hotel dining offer at {merchant} in {city}, such as a breakfast package or dinner menu. "
        "Confirm today's inclusions with the hotel before you book.",
    ),
}


def is_policy_violation(*parts: str | None) -> bool:
    blob = " ".join(part for part in parts if part)
    if not blob.strip():
        return False
    return bool(_POLICY_RE.search(blob))


def explicit_price_comparison(text: str | None) -> bool:
    if not text:
        return False
    return bool(_COMPARISON_RE.search(text))


def is_low_value_title(title: str | None, merchant: str) -> bool:
    """True when a title is homepage chrome or a repeated brand, not an offer."""
    text = (title or "").strip()
    if not text:
        return True
    if _CHROME_RE.search(text):
        return True
    if _OFFER_RE.search(text):
        return False
    if ":" in text:
        return True
    merchant_norm = _norm(merchant)
    title_norm = _norm(text)
    return bool(merchant_norm) and title_norm == merchant_norm


def publisher_listing(
    merchant: str,
    city: str | None,
    venue_category: str | None,
) -> tuple[str, str]:
    category_id = _category_id(venue_category)
    title_tmpl, body_tmpl = _PUBLISHER_COPY.get(
        category_id,
        _PUBLISHER_COPY["restaurants-cafes-bistros"],
    )
    place = (city or "").strip() or "your area"
    name = (merchant or "").strip() or "This venue"
    return (
        title_tmpl.format(merchant=name, city=place)[:255],
        body_tmpl.format(merchant=name, city=place),
    )


def public_original_price(
    deal_price: Decimal,
    original_price: Decimal,
    text: str | None,
    *,
    trust: bool,
) -> Decimal:
    """Drop min/max page amounts that were stored as a fake was/now pair."""
    if trust:
        return original_price
    if deal_price <= 0 or original_price <= deal_price:
        return deal_price if deal_price > 0 else original_price
    savings = (original_price - deal_price) / original_price
    if explicit_price_comparison(text) and Decimal("0.05") <= savings <= Decimal("0.55"):
        return original_price
    return deal_price


def prepare_public_listing(
    *,
    title: str | None,
    description: str | None,
    merchant: str,
    city: str | None,
    venue_category: str | None,
    is_subscriber: bool,
    deal_price: Decimal,
    original_price: Decimal,
    about: str | None = None,
) -> dict[str, object]:
    """Return copy and prices safe to render. ``blocked`` listings stay off the site."""
    if is_policy_violation(title, description, merchant):
        return {
            "blocked": True,
            "title": title,
            "description": description,
            "about": None,
            "deal_price": deal_price,
            "original_price": deal_price,
        }

    about_out = None if is_policy_violation(about) else about
    if is_subscriber:
        shown_title = (title or merchant).strip() or merchant
        shown_description = description
    elif is_low_value_title(title, merchant):
        shown_title, shown_description = publisher_listing(
            merchant, city, venue_category
        )
    else:
        shown_title = (title or merchant).strip()
        if description and _CHROME_RE.search(description):
            _title, shown_description = publisher_listing(
                merchant, city, venue_category
            )
        else:
            shown_description = description

    price_text = " ".join(
        part for part in (shown_title, shown_description) if part
    )
    shown_original = public_original_price(
        deal_price,
        original_price,
        price_text,
        trust=is_subscriber,
    )
    return {
        "blocked": False,
        "title": shown_title,
        "description": shown_description,
        "about": about_out,
        "deal_price": deal_price,
        "original_price": shown_original,
    }


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
