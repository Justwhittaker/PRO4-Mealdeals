"""Dish-aware deal image placeholders (last-resort after deal page + site landing).

FORCE ORDER for deal photos (enforced by the scraper, documented in /scrape skill):
  1. Deal / offer page image
  2. Merchant website landing / menu page image
  3. Dish-category generic placeholder (this module)

Placeholders are keyed by dish type (burger, pasta, vineyard wine, tagine, …).
Unknown dishes can be discovered via Wikimedia Commons and persisted for reuse.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent / "data" / "dish_placeholders.json"

# Seed generics — stable Unsplash CDN URLs (w=800). Prefer dish-specific over
# the old single "default lunch" photo so fallbacks look relevant.
_SEED_PLACEHOLDERS: dict[str, dict[str, Any]] = {
    "burger": {
        "label": "Burger",
        "url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&q=80",
        "keywords": ["burger", "cheeseburger", "hamburger", "smash burger"],
    },
    "pizza": {
        "label": "Pizza",
        "url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80",
        "keywords": ["pizza", "pizzeria", "margherita", "pepperoni"],
    },
    "pasta": {
        "label": "Pasta",
        "url": "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=800&q=80",
        "keywords": ["pasta", "spaghetti", "penne", "lasagna", "lasagne", "ravioli", "carbonara"],
    },
    "sushi": {
        "label": "Sushi",
        "url": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=800&q=80",
        "keywords": ["sushi", "sashimi", "nigiri", "maki", "ramen"],
    },
    "noodles": {
        "label": "Noodles",
        "url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=800&q=80",
        "keywords": ["noodle", "pho", "udon", "pad thai", "ramen bowl"],
    },
    "steak": {
        "label": "Steak",
        "url": "https://images.unsplash.com/photo-1600891964092-4316c288032e?w=800&q=80",
        "keywords": ["steak", "ribeye", "sirloin", "grill steak", "t-bone"],
    },
    "chicken": {
        "label": "Chicken",
        "url": "https://images.unsplash.com/photo-1598103442097-8b74394b95c6?w=800&q=80",
        "keywords": ["chicken", "roast chicken", "peri peri", "nando", "fried chicken", "wings"],
    },
    "seafood": {
        "label": "Seafood",
        "url": "https://images.unsplash.com/photo-1559339352-11d035aa65de?w=800&q=80",
        "keywords": ["seafood", "fish", "salmon", "prawn", "shrimp", "lobster", "oyster"],
    },
    "taco": {
        "label": "Tacos / Mexican",
        "url": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800&q=80",
        "keywords": ["taco", "burrito", "mexican", "chipotle", "quesadilla", "nacho"],
    },
    "sandwich": {
        "label": "Sandwich / Wrap",
        "url": "https://images.unsplash.com/photo-1528735602780-2552afd33c83?w=800&q=80",
        "keywords": ["sandwich", "wrap", "sub ", "baguette", "panini", "ciabatta", "pretzel"],
    },
    "salad": {
        "label": "Salad",
        "url": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=800&q=80",
        "keywords": ["salad", "poke", "bowl", "greens"],
    },
    "breakfast": {
        "label": "Breakfast",
        "url": "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=800&q=80",
        "keywords": ["breakfast", "brunch", "pancake", "waffle", "eggs", "omelette", "pastry"],
    },
    "coffee": {
        "label": "Coffee / Cafe",
        "url": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&q=80",
        "keywords": ["coffee", "espresso", "latte", "cappuccino", "cafe", "café"],
    },
    "dessert": {
        "label": "Dessert",
        "url": "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=800&q=80",
        "keywords": ["dessert", "cake", "ice cream", "chocolate", "pastry", "bakery"],
    },
    "wine_vineyard": {
        "label": "Wine / Vineyard",
        "url": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb?w=800&q=80",
        "keywords": [
            "wine",
            "vineyard",
            "winery",
            "cellar door",
            "wine tasting",
            "wine estate",
            "wine farm",
            "glass of wine",
        ],
    },
    "pub_food": {
        "label": "Pub food",
        "url": "https://images.unsplash.com/photo-1514933651103-005eec06c04b?w=800&q=80",
        "keywords": ["pub", "beer", "ale", "fish and chips", "gastropub", "pint"],
    },
    "hotel_dining": {
        "label": "Hotel dining",
        "url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80",
        "keywords": ["hotel", "resort", "buffet", "room service", "fine dining"],
    },
    "grocery_deli": {
        "label": "Grocery / Deli",
        "url": "https://images.unsplash.com/photo-1542838132-92d30453265a?w=800&q=80",
        "keywords": ["supermarket", "grocery", "deli", "meal deal", "ready meal"],
    },
    "tagine": {
        "label": "Tagine",
        "url": "https://images.unsplash.com/photo-1541518763669-27fef04b14ea?w=800&q=80",
        "keywords": ["tagine", "tajine", "moroccan"],
    },
    "curry": {
        "label": "Curry",
        "url": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800&q=80",
        "keywords": ["curry", "tikka", "masala", "biryani", "indian", "thai curry"],
    },
    "bbq": {
        "label": "BBQ",
        "url": "https://images.unsplash.com/photo-1529193591184-b1d58069ecdd?w=800&q=80",
        "keywords": ["bbq", "barbecue", "ribs", "smokehouse", "grill platter"],
    },
    "restaurant_meal": {
        "label": "Restaurant meal",
        "url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80",
        "keywords": ["restaurant", "lunch", "dinner", "meal deal", "hot meal", "main"],
    },
}

_VENUE_DEFAULTS: dict[str, str] = {
    "Wine Farms & Entertainment Venues": "wine_vineyard",
    "Hotels, Resorts & B&B's": "hotel_dining",
    "Clubs, Bars & Pubs": "pub_food",
    "Deli's and Grocers": "grocery_deli",
    "Food Trucks & Takeaway's": "burger",
    "Restaurants, Cafe's & Bistro's": "restaurant_meal",
}

_learned_cache: dict[str, dict[str, Any]] | None = None


def _load_learned() -> dict[str, dict[str, Any]]:
    global _learned_cache
    if _learned_cache is not None:
        return _learned_cache
    if _DATA_PATH.exists():
        try:
            _learned_cache = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to load dish placeholders from %s", _DATA_PATH)
            _learned_cache = {}
    else:
        _learned_cache = {}
    return _learned_cache


def _save_learned(data: dict[str, dict[str, Any]]) -> None:
    global _learned_cache
    _DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DATA_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _learned_cache = data


def _all_placeholders() -> dict[str, dict[str, Any]]:
    merged = {**_SEED_PLACEHOLDERS, **_load_learned()}
    return merged


def slugify_dish(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.strip().lower())
    return cleaned.strip("_")[:64] or "restaurant_meal"


def _haystack(
    *,
    title: str | None,
    description: str | None,
    merchant: str | None,
    items: list[str] | None,
) -> str:
    parts = [title or "", description or "", merchant or ""]
    if items:
        parts.extend(items)
    return " ".join(parts).lower()


# Vague catch-alls — only used after specific dish keywords miss.
_GENERIC_KEYS = frozenset({"restaurant_meal", "grocery_deli", "hotel_dining", "pub_food"})


def match_dish_key(
    *,
    title: str | None = None,
    description: str | None = None,
    merchant: str | None = None,
    items: list[str] | None = None,
    venue_category: str | None = None,
) -> str:
    """Return the best dish-key for the deal text / venue."""
    text = _haystack(
        title=title, description=description, merchant=merchant, items=items
    )
    placeholders = _all_placeholders()

    def _best(keys: set[str] | frozenset[str] | None = None, *, exclude_generic: bool = False) -> str | None:
        best_key: str | None = None
        best_len = 0
        for key, meta in placeholders.items():
            if exclude_generic and key in _GENERIC_KEYS:
                continue
            if keys is not None and key not in keys:
                continue
            for kw in meta.get("keywords") or []:
                token = str(kw).lower()
                if token and token in text and len(token) > best_len:
                    best_key = key
                    best_len = len(token)
        return best_key

    # 1) Specific dishes first (burger/pasta/chicken/…) — ignore vague generics
    #    so merchant names like "X Restaurant" don't beat "chicken".
    specific = _best(exclude_generic=True)
    if specific:
        return specific

    # 2) Venue-category default (wine farm → vineyard, hotel → hotel dining, …)
    if venue_category and venue_category in _VENUE_DEFAULTS:
        return _VENUE_DEFAULTS[venue_category]

    # 3) Vague keyword generics, then absolute default
    generic = _best(keys=_GENERIC_KEYS)
    return generic or "restaurant_meal"


def placeholder_url_for_key(key: str) -> str:
    placeholders = _all_placeholders()
    meta = placeholders.get(key) or placeholders["restaurant_meal"]
    return str(meta["url"])


def resolve_dish_placeholder(
    *,
    title: str | None = None,
    description: str | None = None,
    merchant: str | None = None,
    items: list[str] | None = None,
    venue_category: str | None = None,
    discover_unknown: bool = False,
) -> tuple[str, str]:
    """
    Return (image_url, dish_key) for last-resort fallback.

    When discover_unknown=True and no keyword match, try to learn a new dish
    placeholder from the deal title (Wikimedia Commons search) and persist it.
    """
    key = match_dish_key(
        title=title,
        description=description,
        merchant=merchant,
        items=items,
        venue_category=venue_category,
    )

    # If we only hit the generic restaurant default, try learning from title.
    if discover_unknown and key == "restaurant_meal" and title:
        learned_key = _maybe_learn_from_title(title)
        if learned_key:
            key = learned_key

    return placeholder_url_for_key(key), key


def _extract_dish_candidate(title: str) -> str | None:
    """Pull a plausible dish token from a deal title (e.g. 'Lamb Tagine Deal')."""
    cleaned = re.sub(r"[^\w\s'-]", " ", title)
    stop = {
        "the",
        "and",
        "with",
        "meal",
        "deal",
        "offer",
        "special",
        "lunch",
        "dinner",
        "breakfast",
        "bundle",
        "combo",
        "city",
        "hot",
        "for",
        "near",
        "scraped",
        "external",
        "listing",
    }
    words = [w for w in cleaned.split() if len(w) > 2 and w.lower() not in stop]
    if not words:
        return None
    # Prefer last content word (often the dish) or a two-word phrase.
    if len(words) >= 2:
        candidate = f"{words[-2]} {words[-1]}"
        if words[-1][0].isupper() or len(words[-1]) >= 5:
            return words[-1]
        return candidate
    return words[0]


def _maybe_learn_from_title(title: str) -> str | None:
    candidate = _extract_dish_candidate(title)
    if not candidate:
        return None
    key = slugify_dish(candidate)
    placeholders = _all_placeholders()
    if key in placeholders:
        return key

    # Re-check keywords against candidate alone.
    for existing_key, meta in placeholders.items():
        for kw in meta.get("keywords") or []:
            if str(kw).lower() in candidate.lower():
                return existing_key

    url = fetch_generic_food_image(candidate)
    if not url:
        return None

    learned = _load_learned()
    learned[key] = {
        "label": candidate.title(),
        "url": url,
        "keywords": [candidate.lower(), key.replace("_", " ")],
        "source": "wikimedia_commons",
    }
    _save_learned(learned)
    logger.info("Learned new dish placeholder %s → %s", key, url)
    return key


def fetch_generic_food_image(dish: str, *, timeout: float = 12.0) -> str | None:
    """Search Wikimedia Commons for a free generic food photo of `dish`."""
    query = f"{dish} food"
    api = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&generator=search&gsrsearch={quote_plus(query)}"
        "&gsrnamespace=6&gsrlimit=8&prop=imageinfo&iiprop=url|mime"
        "&format=json&origin=*"
    )
    headers = {
        "User-Agent": "MealDealsBot/1.0 (deal placeholder learner; contact=dev@mealdeals.local)"
    }
    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(api)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.info("Wikimedia search failed for %s: %s", dish, exc)
        return None

    pages = (payload.get("query") or {}).get("pages") or {}
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        mime = str(info.get("mime") or "")
        url = str(info.get("url") or "")
        if not url.startswith("http"):
            continue
        if mime and not mime.startswith("image/"):
            continue
        if any(skip in url.lower() for skip in (".svg", ".gif", ".pdf")):
            continue
        return url[:500]
    return None


def is_generic_stock_url(url: str | None) -> bool:
    """True when the URL is a last-resort stock/placeholder (not merchant-site)."""
    if not url:
        return True
    lower = url.lower()
    return "unsplash.com" in lower or "example.com" in lower
