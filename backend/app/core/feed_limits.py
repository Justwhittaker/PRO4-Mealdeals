"""Caps for deal-feed memory usage on the web dyno."""

from __future__ import annotations

# Keep feed responses small enough for the Render 512MiB web dyno.
# UI pages only need a ranked page of deals; sitemaps use /deals/sitemap.
MAX_FEED_LIMIT = 500
FEED_OVERFETCH_CAP = 750
MAX_SITEMAP_LIMIT = 500
