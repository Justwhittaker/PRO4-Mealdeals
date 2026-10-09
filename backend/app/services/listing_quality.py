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
        "Lunch Meal Deal",
        "Lunch offer at {merchant} in {city}: a set meal, early-bird, or weekday special. "
        "Confirm today's price and what is included with the venue before you visit.",
    ),
    "food-trucks-takeaways": (
        "Takeaway Deal",
        "Takeaway offer at {merchant} in {city}, such as a meal deal or limited-time menu promotion. "
        "Confirm the current offer with the store before you order.",
    ),
    "wine-farms-entertainment": (
        "Tasting & Dining Offer",
        "Tasting or dining offer at {merchant} in {city}. "
        "Hours and inclusions change, so confirm the current promotion with the venue.",
    ),
    "delis-grocers": (
        "Spend & Save",
        "Grocery offer at {merchant} in {city}, such as money off a shop when you spend a set amount. "
        "Confirm the current threshold on the store's offers page.",
    ),
    "clubs-bars-pubs": (
        "Happy Hour",
        "Drink special at {merchant} in {city}. "
        "Happy-hour times and included drinks change, so confirm them with the venue before you go.",
    ),
    "hotels-resorts-bbs": (
        "Hotel Dining Offer",
        "Hotel dining offer at {merchant} in {city}, such as a breakfast package or dinner menu. "
        "Confirm today's inclusions with the hotel before you book.",
    ),
}

# Words that name the offer type. Adjacent repeats of these are a template
# glitch ("Takeaway Takeaway"), not a brand ("Pizza Pizza").
_KIND_WORDS = frozenset(
    {
        "takeaway",
        "deal",
        "deals",
        "lunch",
        "meal",
        "meals",
        "hotel",
        "dining",
        "offer",
        "offers",
        "happy",
        "hour",
        "shop",
        "discount",
        "tasting",
        "grocery",
        "spend",
        "save",
        "breakfast",
        "bundle",
        "hot",
    }
)

_TEMPLATE_TITLE_RE = re.compile(
    r"(?i)(?:lunch meal deal|takeaway deal|hot meal offer|breakfast bundle|"
    r"happy hour|evening drink specials|"
    r"tasting\s*(?:&|and)\s*dining offer|"
    r"spend\s*(?:&|and)\s*save|shop discount|hotel dining offer|"
    r"bogo\s*/\s*meal offer)\s*[—–-]\s+\S"
)


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


def _word_key(word: str) -> str:
    return re.sub(r"[^a-z0-9&]+", "", word.lower())


def collapse_repeated_kind_words(title: str) -> str:
    """Drop a repeated offer-type word: 'Takeaway Takeaway Deal' → 'Takeaway Deal'.

    Brand repeats such as 'Pizza Pizza' stay. The city after an em dash is
    left as written.
    """
    separator = re.search(r"\s+[—–-]\s+", title)
    if separator:
        head = title[: separator.start()]
        tail = title[separator.start() :]
    else:
        head, tail = title, ""
    kept: list[str] = []
    previous = ""
    for word in head.split():
        key = _word_key(word)
        if kept and key and key == previous and key in _KIND_WORDS:
            continue
        kept.append(word)
        previous = key
    return (" ".join(kept) + tail).strip()


def compose_offer_title(merchant: str, offer: str, city: str | None) -> str:
    """'{merchant} {offer} — {city}' without repeating a kind word the name already ends with."""
    name = (merchant or "").strip() or "This venue"
    offer_words = (offer or "").split()
    name_words = name.split()
    name_keys = [_word_key(word) for word in name_words]
    offer_keys = [_word_key(word) for word in offer_words]
    overlap = 0
    limit = min(len(name_keys), len(offer_keys))
    for size in range(limit, 0, -1):
        if name_keys[-size:] == offer_keys[:size] and any(offer_keys[:size]):
            overlap = size
            break
    rest = " ".join(offer_words[overlap:]).strip()
    head = name if not rest else f"{name} {rest}"
    place = (city or "").strip() or "your area"
    return collapse_repeated_kind_words(f"{head} — {place}")[:255]


def is_generated_template_title(title: str | None) -> bool:
    """True for scraper fallback titles such as 'Apache Pizza Takeaway Deal — Galway'."""
    return bool(_TEMPLATE_TITLE_RE.search(title or ""))


def publisher_listing(
    merchant: str,
    city: str | None,
    venue_category: str | None,
) -> tuple[str, str]:
    category_id = _category_id(venue_category)
    offer, body_tmpl = _PUBLISHER_COPY.get(
        category_id,
        _PUBLISHER_COPY["restaurants-cafes-bistros"],
    )
    place = (city or "").strip() or "your area"
    name = (merchant or "").strip() or "This venue"
    return (
        compose_offer_title(name, offer, place),
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
