"""Caps for deal-feed memory usage on the web dyno."""

from __future__ import annotations

# Keep feed responses small enough for the Render 512MiB web dyno.
# UI pages request a ranked page; sitemaps use /deals/sitemap.
MAX_FEED_LIMIT = 500
# Max lightweight candidate rows scored before pagination (ids/scalars only).
MAX_FEED_CANDIDATES = 20_000
MAX_SITEMAP_LIMIT = 500
