"""Scraper package."""

from __future__ import annotations

from app.scrapers.base import BaseScraper, ScrapedDeal
from app.scrapers.global_retail import GlobalRetailScraper

__all__ = ["BaseScraper", "GlobalRetailScraper", "ScrapedDeal"]
