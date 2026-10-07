"""Scraper package.

The API imports submodules such as ``categories`` on ordinary requests.
Loading the retail scraper here would pull BeautifulSoup, lxml, and the
market catalogue into every web process. Those names still import on demand.
"""

from __future__ import annotations

from typing import Any


def __getattr__(name: str) -> Any:
    if name in {"BaseScraper", "ScrapedDeal"}:
        from app.scrapers.base import BaseScraper, ScrapedDeal

        exports = {"BaseScraper": BaseScraper, "ScrapedDeal": ScrapedDeal}
        globals().update(exports)
        return exports[name]
    if name == "GlobalRetailScraper":
        from app.scrapers.global_retail import GlobalRetailScraper

        globals()["GlobalRetailScraper"] = GlobalRetailScraper
        return GlobalRetailScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["BaseScraper", "GlobalRetailScraper", "ScrapedDeal"]
