"""Trigger Next.js on-demand revalidation after scrape ingest."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal

logger = logging.getLogger(__name__)


def slugify_city(city: str) -> str:
    return city.strip().lower().replace(" ", "-")


def frontend_country_slug(country: str) -> str:
    """Match Next.js routes (GB → uk)."""
    cc = country.strip().upper()
    if cc == "GB":
        return "uk"
    return cc.lower()


def revalidation_plan(
    areas: set[tuple[str, str]] | None = None,
    *,
    include_global: bool = False,
    extra_tags: list[str] | None = None,
) -> dict[str, list[str]]:
    """
    Tags and paths for one revalidate call.

    A city ingest passes include_global=False so only that city's tag and
    the city/country paths are busted. The home page (`/`) and the global
    `deals` tag are reserved for one call at the end of a zone or cycle.
    """
    tags: list[str] = []
    paths: list[str] = []
    countries_seen: set[str] = set()

    for country, city in sorted(areas or set()):
        cc = frontend_country_slug(country)
        slug = slugify_city(city)
        if not cc or not slug:
            continue
        tags.append(f"deals-{cc}-{slug}")
        countries_seen.add(cc)
        paths.append(f"/{cc}/{slug}")

    for cc in sorted(countries_seen):
        paths.append(f"/{cc}")

    if include_global:
        tags.insert(0, "deals")
        paths.insert(0, "/")

    seen = set(tags)
    for tag in extra_tags or []:
        cleaned = tag.strip()
        if cleaned and cleaned not in seen:
            tags.append(cleaned)
            seen.add(cleaned)

    return {"tags": tags, "paths": paths}


def revalidate_after_scrape(
    *,
    areas: set[tuple[str, str]] | None = None,
    include_global: bool = False,
    extra_tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Invalidate cached deal listings on the public site.

    Skips quietly when REVALIDATE_SECRET is unset (local dev).
    City ingests must leave include_global false. Pass include_global once
    per zone, expire job, or other cycle — not once per city.
    """
    settings = get_settings()
    secret = (settings.revalidate_secret or "").strip()
    if not secret:
        logger.debug("Skipping frontend revalidate (REVALIDATE_SECRET unset)")
        return {"skipped": True, "reason": "no_secret"}

    plan = revalidation_plan(
        areas,
        include_global=include_global,
        extra_tags=extra_tags,
    )
    tags = plan["tags"]
    paths = plan["paths"]
    if not tags and not paths:
        return {"skipped": True, "reason": "nothing_to_revalidate"}

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
        reraise_if_fatal(exc)
        logger.warning("Frontend revalidate request failed: %s", exc)
        return {"ok": False, "error": str(exc)}
