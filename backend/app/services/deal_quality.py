"""Shared deal-quality checks for the newsletter and later junk cleanup.

The Friday newsletter drops anything ``rejection_reason`` flags. Scraper
cleanup can call the same function, or ``filter_kept_in_order`` when the
rows are already in the order that should win (first copy of a
merchant+title is kept).
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


class QualityReject(str, Enum):
    """Why a row must not be shown as a dining offer."""

    SPAM = "spam"
    PARKED_DOMAIN = "parked_domain"
    GENERIC_TITLE = "generic_title"
    LODGING_WITHOUT_DINING = "lodging_without_dining"
    PRICE = "price"


# Gambling and scraped-page spam. Word boundaries keep "slotted" / "freestyle".
_SPAM_RE = re.compile(
    r"(?i)("
    r"\bslots?\b|"
    r"\bgacor\b|"
    r"\bcasino\b|"
    r"\bjudi\b|"
    r"\btogel\b|"
    r"\bakunbos\b|"
    r"\bsitus\b|"
    r"pragmatic\s*play|"
    r"\bpg\s*soft\b|"
    r"\bsportsbook\b|"
    r"\bpoker\b|"
    r"\bbetting\b|"
    r"\btaruhan\b|"
    r"\bmaxwin\b|"
    r"\brtp\b|"
    r"bandar\s+game|"
    r"akun\s*demo|"
    r"slot\s+gratis|"
    r"game\s+online\s+resmi|"
    r"terbukti\s+membayar|"
    r"\bporn\b|"
    r"\bxxx\b|"
    r"\bviagra\b|"
    r"\bcialis\b|"
    r"\bmega\d{2,}\b"
    r")"
)

_PARKED_RE = re.compile(
    r"(?i)("
    r"parked\s+domain|"
    r"domain\s+name\s+on\s+hostinger|"
    r"domain\s+(?:name\s+)?(?:is\s+)?for\s+sale|"
    r"buy\s+this\s+domain|"
    r"this\s+domain\s+(?:is\s+)?(?:parked|for\s+sale)|"
    r"hugedomains|"
    r"sedoparking|"
    r"godaddy|"
    r"domain\s+parking"
    r")"
)

# Page chrome and venue-only labels, after punctuation is stripped.
_GENERIC_EXACT = frozenset(
    {
        "hotel details",
        "overview",
        "overview booking",
        "overview and booking",
        "booking",
        "book now",
        "book a room",
        "rooms",
        "rooms and rates",
        "rooms rates",
        "accommodation",
        "home",
        "home page",
        "homepage",
        "welcome",
        "welcome to our website",
        "official site",
        "official website",
        "contact",
        "contact us",
        "about",
        "about us",
        "menu",
        "our menu",
        "sitemap",
        "privacy policy",
        "cookie policy",
        "location",
        "locations",
        "find us",
        "reservations",
    }
)

_SITE_NAMES = frozenset(
    {
        "hostinger",
        "wordpress",
        "wix",
        "squarespace",
        "godaddy",
        "weebly",
        "blogspot",
        "shopify",
    }
)

_LODGING_RE = re.compile(
    r"(?i)\b(?:"
    r"hotels?|"
    r"guest\s*houses?|"
    r"guesthouses?|"
    r"lodging|"
    r"hostels?|"
    r"motels?|"
    r"resorts?|"
    r"bed\s+and\s+breakfast|"
    r"b\s*&\s*b"
    r")\b"
)

_DINING_RE = re.compile(
    r"(?i)("
    r"breakfast|brunch|\blunch\b|\bdinner\b|\bsupper\b|"
    r"\bmeal\b|\bmenu\b|set menu|tasting menu|afternoon tea|"
    r"\brestaurant\b|\bdining\b|\bbistro\b|\bbrasserie\b|\bcaf[eé]\b|"
    r"\bbuffet\b|\bcarvery\b|happy hour|"
    r"\bfood\b|sunday roast|early[- ]bird|"
    r"\bcourses?\b|\bsteak\b|\bpizza\b|\bburger\b|\bpasta\b|"
    r"\bcoffee\b|\bpint\b|\bwine\b|\bcocktail\b|"
    r"\bfish\b|\bchips\b|\bcurry\b|\bsushi\b|\btapas\b|"
    r"\bdessert\b|ice cream|\bgelato\b|\bmains?\b"
    r")"
)

_PERCENT_RE = re.compile(r"(\d+)\s*%")
_FREE_RE = re.compile(
    r"(?i)\b(free|complimentary|on the house|bogo|buy one get one|2 for 1|two for one)\b"
)
_BOGO_RE = re.compile(r"(?i)\bbogo\b|buy one get one|2 for 1|two for one")


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _coerce_price(value: Decimal | str | int | float | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def duplicate_key(merchant_name: str | None, title: str | None) -> tuple[str, str]:
    """Identity for "same merchant + title" copies."""
    return (_norm(merchant_name), _norm(title))


def promotional_price_label(title: str | None, description: str | None) -> str | None:
    """Label for a % off or free-item offer when there is no positive price."""
    text = " ".join(part for part in (title, description) if part)
    if not text.strip():
        return None
    match = _PERCENT_RE.search(text)
    if match:
        return f"{match.group(1)}% off"
    if _FREE_RE.search(text):
        if _BOGO_RE.search(text):
            return "Buy one, get one"
        return "Free"
    return None


def _core_title(title: str, merchant: str) -> str:
    """Title with the venue name removed, for generic-page checks."""
    norm_title = _norm(title)
    norm_merchant = _norm(merchant)
    if not norm_title:
        return ""
    if norm_merchant and norm_title == norm_merchant:
        return ""
    parts = re.split(r"\s*(?::|\||\s[-–—]\s)\s*", title.strip())
    if len(parts) >= 2:
        head = _norm(parts[0])
        tail = _norm(parts[-1])
        merchant_matches = bool(norm_merchant) and (
            head == norm_merchant
            or head.startswith(norm_merchant)
            or norm_merchant.startswith(head)
        )
        if merchant_matches or tail in _GENERIC_EXACT:
            return tail
    if norm_merchant and norm_title.startswith(norm_merchant + " "):
        return norm_title[len(norm_merchant) + 1 :]
    return norm_title


def _is_generic_title(title: str | None, merchant: str | None) -> bool:
    raw = (title or "").strip()
    if not raw:
        return True
    norm_title = _norm(raw)
    if norm_title in _GENERIC_EXACT or norm_title in _SITE_NAMES:
        return True
    core = _core_title(raw, merchant or "")
    if not core or core in _GENERIC_EXACT or core in _SITE_NAMES:
        return True
    return False


def _category_is_lodging(category: str | None) -> bool:
    text = _norm(category)
    if not text:
        return False
    if text in {
        "hotels resorts b b s",
        "hotels resorts bbs",
        "hotel",
        "hotels",
        "lodging",
        "guest house",
        "guesthouse",
        "hostel",
        "motel",
        "resort",
        "bed and breakfast",
    }:
        return True
    if "hotel" in text and ("resort" in text or "b b" in text):
        return True
    return False


def _is_lodging(
    *,
    title: str | None,
    merchant_name: str | None,
    venue_category: str | None,
) -> bool:
    if _category_is_lodging(venue_category):
        return True
    blob = " ".join(part for part in (merchant_name, title) if part)
    return bool(_LODGING_RE.search(blob))


def _has_dining_offer(title: str | None, description: str | None) -> bool:
    blob = " ".join(part for part in (title, description) if part)
    return bool(_DINING_RE.search(blob))


def rejection_reason(
    *,
    title: str | None,
    description: str | None = None,
    merchant_name: str | None = None,
    venue_category: str | None = None,
    deal_price: Decimal | str | int | float | None = None,
) -> QualityReject | None:
    """Return why this row is junk, or None when it can be shown.

    Rules, in order:
    - spam / gambling keywords (slot, gacor, casino, judi, togel, and the
      related scraped-page phrases)
    - parked or for-sale domain titles
    - titles that are only the venue name, a site name, or generic page
      chrome ("Hotel Details", "Overview & Booking")
    - hotels, guest houses, and other lodging unless the title or
      description states a real dining offer
    - missing or non-positive prices, unless the copy is a percent-off
      or free-item offer
    """
    blob = " ".join(part for part in (title, description, merchant_name) if part)
    if _SPAM_RE.search(blob):
        return QualityReject.SPAM
    if _PARKED_RE.search(blob):
        return QualityReject.PARKED_DOMAIN
    if _is_generic_title(title, merchant_name):
        return QualityReject.GENERIC_TITLE
    if _is_lodging(
        title=title,
        merchant_name=merchant_name,
        venue_category=venue_category,
    ) and not _has_dining_offer(title, description):
        return QualityReject.LODGING_WITHOUT_DINING
    amount = _coerce_price(deal_price)
    if amount is None or amount <= 0:
        if promotional_price_label(title, description) is None:
            return QualityReject.PRICE
    return None


def filter_kept_in_order(
    rows: Sequence[T],
    *,
    title: Callable[[T], str | None],
    merchant_name: Callable[[T], str | None],
    description: Callable[[T], str | None] | None = None,
    venue_category: Callable[[T], str | None] | None = None,
    deal_price: Callable[[T], Decimal | str | int | float | None] | None = None,
) -> list[T]:
    """Drop junk, then drop later copies of the same merchant and title.

    Pass rows in the order that should win. The newsletter ranks by
    location first and then calls this helper.
    """
    read_description = description or (lambda _row: "")
    read_category = venue_category or (lambda _row: None)
    read_price = deal_price or (lambda _row: None)
    kept: list[T] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        row_title = title(row)
        row_merchant = merchant_name(row)
        reason = rejection_reason(
            title=row_title,
            description=read_description(row),
            merchant_name=row_merchant,
            venue_category=read_category(row),
            deal_price=read_price(row),
        )
        if reason is not None:
            continue
        key = duplicate_key(row_merchant, row_title)
        if key in seen:
            continue
        seen.add(key)
        kept.append(row)
    return kept
