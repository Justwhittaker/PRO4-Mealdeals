"""Area-aware retail meal-deal scraper for English-speaking markets."""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

from app.scrapers.base import BaseScraper, ScrapedDeal
from app.scrapers.categories import categorize_venue
from app.scrapers.deal_placeholders import resolve_dish_placeholder
from app.scrapers.local_discovery import discover_local_venues, merge_local_sources
from app.scrapers.hub_radius import hub_default_locality
from app.scrapers.markets import (
    COUNTRY_ALIASES,
    DEFAULT_CITY,
    DEFAULT_CURRENCY,
    MARKET_CITIES,
    MARKET_SOURCES,
    NEW_MARKETS,
    TARGET_MARKETS,
    iter_market_areas,
)

logger = logging.getLogger(__name__)

__all__ = [
    "COUNTRY_ALIASES",
    "DEFAULT_CITY",
    "DEFAULT_CURRENCY",
    "MARKET_CITIES",
    "MARKET_SOURCES",
    "NEW_MARKETS",
    "TARGET_MARKETS",
    "GlobalRetailScraper",
    "iter_market_areas",
]

# Curated offer-style templates when live HTML has no parseable offer copy.
# NEVER invent numeric prices — leave priced=False so UI hides money and shows
# the deal type (happy hour, BOGO, lunch special, etc.).
# Image fallbacks are dish-aware via deal_placeholders (not per-merchant stock).

_AREA_DEAL_TEMPLATES: list[dict[str, object]] = [
    {
        "title": "{merchant} Lunch Meal Deal — {city}",
        "description": (
            "Main + side + drink combo offer for {city}. "
            "Confirm today's inclusions and price in-store or on the merchant site."
        ),
        "priced": False,
        "main": "Sandwich or wrap",
        "side": "Crisps or fruit",
        "drink": "Soft drink",
    },
    {
        "title": "{merchant} Hot Meal Offer — {city}",
        "description": (
            "Hot lunch special near {city}. "
            "Verify offer details before visiting."
        ),
        "priced": False,
        "main": "Hot main",
        "side": "Side salad",
        "drink": "Drink",
    },
    {
        "title": "{merchant} Breakfast Bundle — {city}",
        "description": (
            "Breakfast meal deal for {city}. "
            "See merchant site for current bundle contents."
        ),
        "priced": False,
        "main": "Breakfast roll",
        "side": "Pastry",
        "drink": "Coffee or tea",
    },
]

_BAR_PUB_TEMPLATES: list[dict[str, object]] = [
    {
        "title": "{merchant} Happy Hour — {city}",
        "description": (
            "Time-limited drink specials near {city} "
            "(e.g. all cocktails half price in early evening). "
            "Check the venue for today's hours and included drinks."
        ),
        "priced": False,
        "main": "Drink special",
        "side": "Bar snack",
        "drink": "Happy hour pour",
    },
    {
        "title": "{merchant} Evening Drink Specials — {city}",
        "description": (
            "Pub and bar promotions for {city}: 2-for-1, half-price pours, "
            "or selected cocktails on special. Confirm times on arrival."
        ),
        "priced": False,
        "main": "Selected drinks",
        "side": "Sharer plate",
        "drink": "House special",
    },
]

_TAKEAWAY_TEMPLATES: list[dict[str, object]] = [
    {
        "title": "{merchant} Takeaway Deal — {city}",
        "description": (
            "Chain takeaway promotion for {city} — often buy-one-get-one-free, "
            "meal deals, or limited-time pizza offers. See merchant deals page "
            "for the current offer type (price may vary by store)."
        ),
        "priced": False,
        "main": "Pizza or meal",
        "side": "Sides",
        "drink": "Soft drink",
    },
    {
        "title": "{merchant} BOGO / Meal Offer — {city}",
        "description": (
            "Buy-one-get-one or multi-buy takeaway special serving {city}. "
            "Offer is described by type rather than a fixed listed price."
        ),
        "priced": False,
        "main": "Main takeaway",
        "side": "Side",
        "drink": "Drink",
    },
]

_GROCER_TEMPLATES: list[dict[str, object]] = [
    {
        "title": "{merchant} Spend & Save — {city}",
        "description": (
            "Grocery voucher for {city}: spend a set amount on your shop and "
            "get money off at checkout (e.g. spend €50 get €10 off). "
            "Confirm the current threshold and voucher on the merchant offers page."
        ),
        "priced": False,
        "main": "Grocery shop",
        "side": "Store voucher",
        "drink": "Checkout saving",
    },
    {
        "title": "{merchant} Shop Discount — {city}",
        "description": (
            "Percentage or money-off promotion on your {city} grocery shop "
            "(e.g. 20% off selected lines, or €10 off when you spend €50). "
            "Offer type shown instead of a single meal price."
        ),
        "priced": False,
        "main": "Basket special",
        "side": "Multibuy",
        "drink": "Checkout discount",
    },
]

_OFFER_SNIPPET_RE = re.compile(
    r"(?is)("
    r"happy\s*hours?\b.{0,100}"
    r"|all\s+cocktails?\s+half\s+price.{0,80}"
    r"|half\s+price\s+(?:on\s+)?(?:all\s+)?(?:cocktails?|drinks?|pints?|beer).{0,80}"
    r"|buy\s+one\s+get\s+one(?:\s+free)?.{0,80}"
    r"|\bbogo\b.{0,60}"
    r"|2\s*[- ]?for\s*[- ]?1\b.{0,60}"
    r"|two\s+for\s+(?:the\s+price\s+of\s+)?one.{0,60}"
    # Grocery spend-threshold / money-off / % off the shop
    # e.g. Spend €50 and get €10 off / spend 50 euro get 10 euro off
    r"|spend\s+(?:€|£|\$)?\s?\d+[\d.,]*\s*(?:euros?|eur|gbp|usd|pounds?)?\s*"
    r"(?:(?:and|&|to)\s+)?(?:get|receive|save|enjoy)\s+"
    r"(?:€|£|\$)?\s?\d+[\d.,]*\s*(?:euros?|eur|gbp|usd|pounds?)?\s*"
    r"(?:%\s*)?off.{0,50}"
    r"|(?:get|save|receive)\s+(?:€|£|\$)?\s?\d+[\d.,]*\s*"
    r"(?:euros?|eur|pounds?)?\s*off\s+(?:when\s+you\s+)?spend\s+"
    r"(?:€|£|\$)?\s?\d+[\d.,]*\s*(?:euros?|eur|pounds?)?.{0,40}"
    r"|(?:€|£|\$)\s?\d+[\d.,]*\s*off\s+(?:when\s+you\s+)?"
    r"(?:spend\s+(?:€|£|\$)?\s?\d+[\d.,]*|(?:your\s+)?(?:shop|basket|grocery)).{0,40}"
    r"|\d+\s*%\s*off(?:\s+your\s+(?:shop|basket|grocery|entire\s+shop))?.{0,50}"
    r"|money\s+off\s+(?:your\s+)?(?:shop|basket|grocery).{0,50}"
    r"|voucher\s+(?:worth\s+)?(?:€|£|\$)?\s?\d+[\d.,]*.{0,40}"
    r")"
)

_THRESHOLD_OFFER_RE = re.compile(
    r"(?i)spend|when you spend|%\s*off|off your (?:shop|basket|grocery)|"
    r"money off|voucher|save \d|get \d.+off"
)


def _templates_for_category(venue_category: str) -> list[dict[str, object]]:
    if venue_category == "Clubs, Bars & Pubs":
        return _BAR_PUB_TEMPLATES
    if venue_category == "Food Trucks & Takeaway's":
        return _TAKEAWAY_TEMPLATES
    if venue_category == "Deli's and Grocers":
        return _GROCER_TEMPLATES
    return _AREA_DEAL_TEMPLATES


def _is_threshold_or_percent_offer(snippet: str) -> bool:
    """True when copy is spend/get-off or % off — not a unit meal price."""
    return bool(_THRESHOLD_OFFER_RE.search(snippet or ""))


def _clean_offer_snippet(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip(" .-•|")
    if len(text) > 220:
        text = text[:217].rstrip() + "..."
    return text


class GlobalRetailScraper(BaseScraper):
    """
    Skims public promo pages when reachable, otherwise publishes
    area-localised external deal cards so city feeds stay populated.
    """

    name = "global_retail"

    def __init__(self, timeout: float = 20.0) -> None:
        super().__init__(timeout=timeout)
        # Cache live HTML parses by URL so multi-city runs don't re-hit merchants.
        self._live_cache: dict[str, dict[str, Decimal | str]] = {}
        # Homepage media fallbacks keyed by origin (scheme://host).
        self._site_media_cache: dict[str, dict[str, str]] = {}

    def _normalize_country(self, country_code: str) -> str:
        upper = country_code.strip().upper()
        return COUNTRY_ALIASES.get(upper, upper)

    async def scrape(
        self,
        country_code: str,
        city: str | None = None,
    ) -> list[ScrapedDeal]:
        country = self._normalize_country(country_code)
        sources = list(MARKET_SOURCES.get(country, []))
        currency = DEFAULT_CURRENCY.get(country, "USD")
        city_name = (city or DEFAULT_CITY.get(country, "Unknown")).replace("-", " ").title()

        # Mom-and-pop / independent venues for this city (OSM + cache), all
        # hospitality categories — not limited to national chains.
        try:
            local_sources = await discover_local_venues(country, city_name)
            sources = merge_local_sources(sources, local_sources)
        except Exception as exc:  # noqa: BLE001 — discovery must not fail scrape
            logger.info("Local venue discovery failed for %s / %s: %s", city_name, country, exc)

        if not sources:
            logger.info("No market sources configured for %s / %s", country, city_name)
            return []

        deals: list[ScrapedDeal] = []

        for index, source in enumerate(sources):
            live = await self._try_live_parse(source["url"], source["merchant"])
            venue_category = str(
                source.get("venue_category") or categorize_venue(source["merchant"])
            )
            templates = _templates_for_category(venue_category)
            template = templates[index % len(templates)]

            title = live.get("title") or str(template["title"]).format(
                merchant=source["merchant"], city=city_name
            )
            description = live.get("description") or str(
                template["description"]
            ).format(city=city_name)
            if live.get("offer_snippet") and not live.get("description"):
                description = str(live["offer_snippet"])

            # Never invent prices. 0/0 means "hide pricing; show deal copy".
            if "deal_price" in live:
                deal_price = Decimal(str(live["deal_price"]))
                if "original_price" in live:
                    original = Decimal(str(live["original_price"]))
                else:
                    # Single listed price — show it, no fabricated "was" price.
                    original = deal_price
            else:
                deal_price = Decimal("0")
                original = Decimal("0")

            # FORCE photo order:
            # 1) deal/offer page  2) site landing/menu  3) dish-category generic
            image_url = live.get("image_url")
            if not image_url:
                item_names = [
                    str(template["main"]),
                    str(template["side"]),
                    str(template["drink"]),
                ]
                image_url, dish_key = resolve_dish_placeholder(
                    title=str(title),
                    description=str(description),
                    merchant=source["merchant"],
                    items=item_names,
                    venue_category=venue_category,
                    discover_unknown=True,
                )
                logger.info(
                    "No site image for %s (%s) — dish placeholder '%s'",
                    source["merchant"],
                    urlparse(source["url"]).netloc,
                    dish_key,
                )
            logo_url = live.get("logo_url")

            area_local = str(
                source.get("area_local") or hub_default_locality(city_name)
            )
            # Unique URL per hub + nested town so the same chain can appear in multiple areas
            raw_url = (
                f"{source['url']}?city={quote_plus(city_name)}"
                f"&locality={quote_plus(area_local)}"
                f"&country={country}&utm_source=mealdeals_scraper"
            )

            website = str(live.get("website") or source["url"]).split("?")[0]
            phone = str(live["phone"]) if live.get("phone") else None
            email = str(live["email"]) if live.get("email") else None
            about_blurb = (
                str(live["about_blurb"]) if live.get("about_blurb") else None
            )

            item_price = (
                str(deal_price.quantize(Decimal("0.01")))
                if deal_price > 0
                else "0"
            )
            deals.append(
                ScrapedDeal(
                    merchant_name=source["merchant"],
                    title=str(title)[:255],
                    description=str(description),
                    raw_url=raw_url,
                    original_price=original,
                    deal_price=deal_price,
                    currency_code=currency,
                    country_code=country,
                    city=city_name,
                    area_hub=city_name,
                    area_local=area_local,
                    items=[
                        {
                            "category": "main",
                            "item_name": str(template["main"]),
                            "individual_price": item_price,
                        },
                        {
                            "category": "side",
                            "item_name": str(template["side"]),
                            "individual_price": "0",
                        },
                        {
                            "category": "drink",
                            "item_name": str(template["drink"]),
                            "individual_price": "0",
                        },
                    ],
                    language_code="en",
                    image_url=str(image_url)[:500] if image_url else None,
                    logo_url=str(logo_url)[:500] if logo_url else None,
                    website=website[:500],
                    phone=phone,
                    email=email,
                    about_blurb=about_blurb,
                    venue_category=venue_category,
                )
            )

        logger.info("Scraped %d deals for %s / %s", len(deals), city_name, country)
        return deals

    async def _try_live_parse(
        self, url: str, merchant: str
    ) -> dict[str, Decimal | str]:
        """Best-effort HTML skim; returns empty dict if blocked or unparseable."""
        if url in self._live_cache:
            return self._live_cache[url]

        try:
            html = await self.fetch_html(url)
        except Exception as exc:
            logger.info("Live fetch skipped for %s: %s", merchant, exc)
            self._live_cache[url] = {}
            return {}

        if not html or len(html) < 200:
            self._live_cache[url] = {}
            return {}

        soup = self.parse_soup(html)
        title = None
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            title = str(og["content"]).strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        description = None
        od = soup.find("meta", property="og:description") or soup.find(
            "meta", attrs={"name": "description"}
        )
        if od and od.get("content"):
            description = str(od["content"]).strip()

        image_url = self._extract_deal_image_url(soup, page_url=url)
        logo_url = self._extract_logo_url(soup, page_url=url)
        if not image_url or not logo_url:
            site_media = await self._fetch_site_media(url)
            if not image_url:
                image_url = site_media.get("image_url") or None
            if not logo_url:
                logo_url = site_media.get("logo_url") or None

        contact = self._extract_business_contact(
            soup, page_url=url, merchant=merchant, description=description
        )

        page_text = soup.get_text(" ", strip=True)[:12000]
        prices = self._extract_prices(page_text)
        offer_snippet = self._extract_offer_snippet(page_text)
        result: dict[str, Decimal | str] = {}
        if title:
            result["title"] = f"{merchant}: {title}"[:255]
        if description:
            result["description"] = description[:1000]
        elif offer_snippet:
            result["description"] = offer_snippet[:1000]
            result["title"] = result.get("title") or f"{merchant}: {offer_snippet}"[:255]
        if offer_snippet:
            result["offer_snippet"] = offer_snippet[:1000]
        if image_url:
            result["image_url"] = image_url
        if logo_url:
            result["logo_url"] = logo_url
        result.update(contact)
        # Only persist prices actually found on the page — never invent a
        # comparison / "was" price (e.g. 1.6x) when one amount is missing.
        # Spend €50 / get €10 off (and % off shop) are offer *types*, not a
        # meal deal unit price — keep money hidden and state the voucher copy.
        threshold_offer = bool(
            offer_snippet and _is_threshold_or_percent_offer(str(offer_snippet))
        )
        if threshold_offer:
            pass
        elif len(prices) >= 2:
            prices_sorted = sorted(prices)
            result["deal_price"] = prices_sorted[0]
            result["original_price"] = prices_sorted[-1]
        elif len(prices) == 1:
            result["deal_price"] = prices[0]
        self._live_cache[url] = result
        return result

    async def _fetch_site_media(self, page_url: str) -> dict[str, str]:
        """Fallback: content photo + logo from homepage / menu / about paths."""
        parsed = urlparse(page_url)
        if not parsed.scheme or not parsed.netloc:
            return {}
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._site_media_cache:
            return self._site_media_cache[origin]

        media: dict[str, str] = {}
        # Try a few high-signal pages — many chains bury food photos on /menu.
        for path in ("/", "/menu", "/our-menu", "/menus", "/food", "/about"):
            candidate_url = f"{origin}{path}"
            try:
                html = await self.fetch_html(candidate_url)
            except Exception as exc:
                logger.info("Site media fetch skipped for %s: %s", candidate_url, exc)
                continue
            if not html or len(html) < 200:
                continue
            soup = self.parse_soup(html)
            if not media.get("image_url"):
                image_url = self._extract_deal_image_url(soup, page_url=candidate_url)
                if image_url:
                    media["image_url"] = image_url
            if not media.get("logo_url"):
                logo_url = self._extract_logo_url(soup, page_url=candidate_url)
                if logo_url:
                    media["logo_url"] = logo_url
            if media.get("image_url") and media.get("logo_url"):
                break

        self._site_media_cache[origin] = media
        return media

    def _extract_business_contact(
        self,
        soup: Any,
        *,
        page_url: str,
        merchant: str,
        description: str | None,
    ) -> dict[str, str]:
        """Pull name/website/phone/email/about from HTML + JSON-LD."""
        out: dict[str, str] = {
            "website": f"{urlparse(page_url).scheme}://{urlparse(page_url).netloc}/"
        }

        # JSON-LD LocalBusiness / Organization / Restaurant
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text() or ""
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                typ = node.get("@type")
                types = (
                    [typ]
                    if isinstance(typ, str)
                    else (typ if isinstance(typ, list) else [])
                )
                if not any(
                    str(t).lower()
                    in {
                        "localbusiness",
                        "restaurant",
                        "foodestablishment",
                        "organization",
                        "cafeorcoffeeshop",
                        "barorpub",
                        "hotel",
                    }
                    for t in types
                ):
                    # Still accept if contact fields present
                    if not (node.get("telephone") or node.get("email")):
                        continue
                if node.get("name") and not out.get("business_name"):
                    out["business_name"] = str(node["name"])[:255]
                if node.get("url") and str(node["url"]).startswith("http"):
                    out["website"] = str(node["url"])[:500]
                if node.get("telephone"):
                    out["phone"] = str(node["telephone"])[:64]
                if node.get("email"):
                    out["email"] = str(node["email"])[:255]
                about = node.get("description") or node.get("disambiguatingDescription")
                if about and not out.get("about_blurb"):
                    out["about_blurb"] = self._short_blurb(str(about))

        mailto = soup.find("a", href=re.compile(r"^mailto:", re.I))
        if mailto and mailto.get("href") and "email" not in out:
            out["email"] = str(mailto["href"]).split(":", 1)[1].split("?")[0][:255]

        tel = soup.find("a", href=re.compile(r"^tel:", re.I))
        if tel and tel.get("href") and "phone" not in out:
            out["phone"] = str(tel["href"]).split(":", 1)[1][:64]

        if "about_blurb" not in out:
            about_el = (
                soup.find(id=re.compile(r"about", re.I))
                or soup.find(class_=re.compile(r"\babout\b", re.I))
                or soup.find("section", attrs={"aria-label": re.compile(r"about", re.I)})
            )
            if about_el:
                out["about_blurb"] = self._short_blurb(about_el.get_text(" ", strip=True))
            elif description:
                out["about_blurb"] = self._short_blurb(description)

        if "business_name" not in out:
            out["business_name"] = merchant
        return out

    def _short_blurb(self, text: str, max_len: int = 280) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) <= max_len:
            return cleaned
        clipped = cleaned[: max_len - 1].rsplit(" ", 1)[0]
        return f"{clipped}…"

    def _absolutize_media_url(self, raw: str, *, page_url: str) -> str | None:
        absolute = urljoin(page_url, raw.strip())
        if absolute.startswith(("http://", "https://")):
            return absolute[:500]
        return None

    def _looks_like_tracking_or_icon(self, src: str) -> bool:
        lower = src.lower()
        return any(
            token in lower
            for token in (
                "sprite",
                "pixel",
                "1x1",
                "tracking",
                "spacer",
                "blank.gif",
                "data:image",
                "placeholder",
                "placeholder.png",
                "placeholder.svg",
                "placeholder.jpg",
            )
        )

    def _is_logoish_url(self, src: str) -> bool:
        lower = src.lower()
        return any(
            token in lower
            for token in ("icon", "logo", "favicon", "wordmark", "brand-mark")
        )

    def _pick_from_srcset(self, srcset: str) -> str | None:
        """Pick the widest candidate from a srcset attribute."""
        best_url: str | None = None
        best_w = -1
        for part in srcset.split(","):
            bits = part.strip().split()
            if not bits:
                continue
            url = bits[0]
            width = 0
            if len(bits) > 1 and bits[1].endswith("w"):
                try:
                    width = int(bits[1][:-1])
                except ValueError:
                    width = 0
            if width >= best_w:
                best_w = width
                best_url = url
        return best_url

    def _img_candidate_urls(self, img: Any) -> list[str]:
        """Collect src / data-src / srcset URLs from an <img> or <source>."""
        found: list[str] = []
        for attr in (
            "src",
            "data-src",
            "data-lazy-src",
            "data-original",
            "data-image",
        ):
            val = img.get(attr)
            if val and isinstance(val, str) and val.strip():
                found.append(val.strip())
        for attr in ("srcset", "data-srcset"):
            val = img.get(attr)
            if val and isinstance(val, str):
                picked = self._pick_from_srcset(val)
                if picked:
                    found.append(picked)
        return found

    def _json_ld_images(self, soup: Any) -> list[str]:
        out: list[str] = []
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text() or ""
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                image = node.get("image")
                if isinstance(image, str):
                    out.append(image.strip())
                elif isinstance(image, list):
                    for item in image:
                        if isinstance(item, str):
                            out.append(item.strip())
                        elif isinstance(item, dict) and item.get("url"):
                            out.append(str(item["url"]).strip())
                elif isinstance(image, dict) and image.get("url"):
                    out.append(str(image["url"]).strip())
        return out

    def _extract_deal_image_url(self, soup: Any, *, page_url: str) -> str | None:
        """Deal hero from offer page: promo img → og/twitter → JSON-LD → content img."""
        candidates: list[str] = []

        # Prefer obvious offer / hero / menu imagery before generic meta tags.
        for img in soup.find_all(["img", "source"]):
            for src in self._img_candidate_urls(img):
                if src.startswith("data:") or self._looks_like_tracking_or_icon(src):
                    continue
                if self._is_logoish_url(src):
                    continue
                attrs = " ".join(
                    str(img.get(key) or "")
                    for key in ("alt", "class", "id", "src", "data-src")
                ).lower()
                if any(
                    token in attrs
                    for token in (
                        "hero",
                        "promo",
                        "offer",
                        "deal",
                        "banner",
                        "featured",
                        "menu",
                        "food",
                        "dish",
                        "product",
                    )
                ):
                    if not any(skip in attrs for skip in ("logo", "icon", "favicon")):
                        candidates.append(src)

        for prop in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
            tag = soup.find("meta", property=prop) or soup.find(
                "meta", attrs={"name": prop}
            )
            if tag and tag.get("content"):
                content = str(tag["content"]).strip()
                if not self._is_logoish_url(content):
                    candidates.append(content)

        link = soup.find("link", rel=lambda v: v and "image_src" in v)
        if link and link.get("href"):
            href = str(link["href"]).strip()
            if not self._is_logoish_url(href):
                candidates.append(href)

        for src in self._json_ld_images(soup):
            if not self._is_logoish_url(src) and not self._looks_like_tracking_or_icon(
                src
            ):
                candidates.append(src)

        for img in soup.find_all("img"):
            for src in self._img_candidate_urls(img):
                if src.startswith("data:") or self._looks_like_tracking_or_icon(src):
                    continue
                try:
                    width = int(img.get("width") or 0)
                    height = int(img.get("height") or 0)
                except ValueError:
                    width, height = 0, 0
                if width and height and (width < 120 or height < 80):
                    continue
                lower = src.lower()
                if self._is_logoish_url(lower):
                    continue
                if lower.endswith(".svg") or lower.endswith(".gif"):
                    continue
                candidates.append(src)
                if len(candidates) >= 24:
                    break
            if len(candidates) >= 24:
                break

        for raw in candidates:
            absolute = self._absolutize_media_url(raw, page_url=page_url)
            if absolute and "images.unsplash.com" not in absolute.lower():
                return absolute
        # Allow Unsplash only if it was explicitly on the merchant page (rare).
        for raw in candidates:
            absolute = self._absolutize_media_url(raw, page_url=page_url)
            if absolute:
                return absolute
        return None

    def _extract_logo_url(self, soup: Any, *, page_url: str) -> str | None:
        """Company logo — separate from deal hero photo."""
        candidates: list[str] = []

        # Header / nav logos first (brand mark like Nando's chicken).
        for img in soup.find_all("img"):
            for src in self._img_candidate_urls(img):
                if src.startswith("data:") or self._looks_like_tracking_or_icon(src):
                    continue
                attrs = " ".join(
                    str(img.get(key) or "")
                    for key in ("alt", "class", "id", "src", "data-src")
                ).lower()
                if any(token in attrs for token in ("logo", "brand", "wordmark", "rooster")):
                    candidates.append(src)

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text() or ""
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                logo = node.get("logo")
                if isinstance(logo, str):
                    candidates.append(logo.strip())
                elif isinstance(logo, dict) and logo.get("url"):
                    candidates.append(str(logo["url"]).strip())

        for rel_name in ("apple-touch-icon", "apple-touch-icon-precomposed", "icon"):
            for link in soup.find_all("link", href=True):
                rel = link.get("rel")
                rel_tokens = (
                    [str(r).lower() for r in rel]
                    if isinstance(rel, list)
                    else str(rel or "").lower().split()
                )
                if rel_name in rel_tokens or (
                    rel_name == "icon" and any("icon" in t for t in rel_tokens)
                ):
                    candidates.append(str(link["href"]).strip())

        for raw in candidates:
            if self._looks_like_tracking_or_icon(raw):
                continue
            absolute = self._absolutize_media_url(raw, page_url=page_url)
            if absolute:
                return absolute
        return None

    def _extract_offer_snippet(self, text: str) -> str | None:
        """Pull happy-hour / BOGO / half-price style copy when present."""
        match = _OFFER_SNIPPET_RE.search(text or "")
        if not match:
            return None
        return _clean_offer_snippet(match.group(1))

    def _extract_prices(self, text: str) -> list[Decimal]:
        pattern = re.compile(
            r"(?:£|€|\$|R|₹|A\$|C\$|S\$|NZ\$)\s?(\d{1,3}(?:[.,]\d{2})?)"
        )
        found: list[Decimal] = []
        for match in pattern.finditer(text):
            raw = match.group(1).replace(",", ".")
            try:
                value = Decimal(raw)
            except InvalidOperation:
                continue
            if Decimal("1") <= value <= Decimal("100"):
                found.append(value)
            if len(found) >= 8:
                break
        return found

    async def scrape_all_markets(
        self, country_codes: list[str] | None = None
    ) -> dict[str, list[ScrapedDeal]]:
        results: dict[str, list[ScrapedDeal]] = {}
        for country, city in iter_market_areas(country_codes):
            key = f"{country}:{city}"
            results[key] = await self.scrape(country, city)
        return results
