"""Trigger Next.js on-demand revalidation after scrape ingest."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def slugify_city(city: str) -> str:
    return city.strip().lower().replace(" ", "-")


def frontend_country_slug(country: str) -> str:
    """Match Next.js routes (GB → uk)."""
    cc = country.strip().upper()
    if cc == "GB":
        return "uk"
    return cc.lower()


def revalidate_after_scrape(
    *,
    areas: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Invalidate cached deal listings on the public site.

    Skips quietly when REVALIDATE_SECRET is unset (local dev).
    """
    settings = get_settings()
    secret = (settings.revalidate_secret or "").strip()
    if not secret:
        logger.debug("Skipping frontend revalidate (REVALIDATE_SECRET unset)")
        return {"skipped": True, "reason": "no_secret"}

    tags: list[str] = ["deals"]
    paths: list[str] = ["/"]
    countries_seen: set[str] = set()

    for country, city in sorted(areas or set()):
        cc = frontend_country_slug(country)
        slug = slugify_city(city)
        tags.append(f"deals-{cc}-{slug}")
        countries_seen.add(cc)
        paths.append(f"/{cc}/{slug}")

    for cc in sorted(countries_seen):
        paths.append(f"/{cc}")

    base = settings.frontend_base_url.rstrip("/")
    url = f"{base}/api/revalidate"
    payload = {"secret": secret, "tags": tags, "paths": paths}

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
        if resp.status_code >= 400:
            logger.warning(
                "Frontend revalidate failed (%s): %s",
                resp.status_code,
                resp.text[:500],
            )
            return {
                "ok": False,
                "status": resp.status_code,
                "detail": resp.text[:500],
            }
        data = resp.json()
        logger.info(
            "Frontend revalidated after scrape (%d tags, %d paths)",
            len(tags),
            len(paths),
        )
        return {"ok": True, **data}
    except Exception as exc:
        logger.warning("Frontend revalidate request failed: %s", exc)
        return {"ok": False, "error": str(exc)}
