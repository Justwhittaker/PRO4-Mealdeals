"""Base scraper abstractions (Playwright / HTTPX stubs)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapedDeal:
    """Normalized deal payload produced by scrapers."""

    merchant_name: str
    title: str
    description: str
    raw_url: str
    original_price: Decimal
    deal_price: Decimal
    currency_code: str
    country_code: str
    city: str
    # Hub city for routing (e.g. Galway) + nested town label (e.g. Tuam).
    area_hub: str | None = None
    area_local: str | None = None
    items: list[dict[str, Any]] = field(default_factory=list)
    language_code: str = "en"
    image_url: str | None = None
    # Company logo (distinct from deal hero image) → merchants.logo_url
    logo_url: str | None = None
    # Business contact fields → marketing_contacts (separate from deals)
    website: str | None = None
    phone: str | None = None
    email: str | None = None
    about_blurb: str | None = None
    venue_category: str | None = None


class BaseScraper(ABC):
    """Async scraper interface. Concrete scrapers may use HTTPX or Playwright."""

    name: str = "base"
    user_agent: str = (
        "DineADealBot/1.0 (+https://dineadeal.com/bot; research)"
    )

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    @abstractmethod
    async def scrape(self, country_code: str) -> list[ScrapedDeal]:
        """Fetch and normalize deals for a country market."""

    async def fetch_html(self, url: str) -> str:
        """HTTPX fetch helper used by lightweight scrapers."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    def parse_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    async def fetch_with_playwright(self, url: str) -> str:
        """
        Playwright async stub.

        Real deployments should install playwright browsers in the worker image.
        This method returns empty HTML when Playwright is unavailable so Celery
        tasks can still exercise the pipeline in CI.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed; returning empty HTML for %s", url)
            return ""

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=self.user_agent)
                await page.goto(url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))
                return await page.content()
            finally:
                await browser.close()
