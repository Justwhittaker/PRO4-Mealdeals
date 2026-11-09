"""Trigger Next.js on-demand revalidation after scrape ingest."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal

logger = logging.getLogger(__name__)

# Vercel Bot Protection answers the home NUC with HTTP 429, this header, and
# an HTML page titled "Vercel Security Checkpoint". The site is up.
_VERCEL_MITIGATED = "x-vercel-mitigated"
_CHECKPOINT_MARK = "Vercel Security Checkpoint"
_CHECKPOINT_STATUS = 429
_LOG_TEXT_LIMIT = 180
_REDIS_URL = re.compile(r"rediss?://\S+", re.IGNORECASE)


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


def _response_excerpt(response: httpx.Response, limit: int = 8192) -> str:
    try:
        text = response.text
    except Exception as exc:
        reraise_if_fatal(exc)
        return ""
    if not text:
        return ""
    return text[:limit]


def is_vercel_security_checkpoint(response: httpx.Response) -> bool:
    """True when Vercel answered with a bot-protection challenge, not an outage.

    The NUC is a home server. Bot Protection / Security Checkpoint returns
    HTTP 429, ``x-vercel-mitigated: challenge``, and an HTML page titled
    "Vercel Security Checkpoint". Either marker on a 429 is enough. Other
    429s (a real rate limit, with neither marker) are failures.
    """
    try:
        status = int(response.status_code)
    except (TypeError, ValueError):
        return False
    if status != _CHECKPOINT_STATUS:
        return False
    mitigated = ""
    headers = getattr(response, "headers", None)
    if headers is not None:
        raw = headers.get(_VERCEL_MITIGATED)
        if raw:
            mitigated = str(raw)
    tokens = {part.strip().lower() for part in mitigated.split(",") if part.strip()}
    if "challenge" in tokens:
        return True
    return _CHECKPOINT_MARK in _response_excerpt(response)


def _log_failure_text(text: str, *, secret: str) -> str:
    """Short failure text safe to log. Drops secrets and collapses HTML."""
    cleaned = text or ""
    if secret:
        cleaned = cleaned.replace(secret, "[redacted]")
    cleaned = _REDIS_URL.sub("[redacted]", cleaned)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return "empty response"
    if len(cleaned) > _LOG_TEXT_LIMIT:
        return cleaned[:_LOG_TEXT_LIMIT] + "…"
    return cleaned


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
            if is_vercel_security_checkpoint(resp):
                # The checkpoint page is a full HTML document. Log the fact
                # of the challenge, not the page, and do not count it as a
                # transport failure for the digest.
                logger.warning("Frontend revalidate failed: Vercel challenge (429)")
                return {
                    "ok": False,
                    "status": resp.status_code,
                    "challenge": True,
                    "detail": "Vercel challenge (429)",
                }
            detail = _log_failure_text(_response_excerpt(resp), secret=secret)
            logger.warning(
                "Frontend revalidate failed (%s): %s",
                resp.status_code,
                detail,
            )
            return {
                "ok": False,
                "status": resp.status_code,
                "detail": detail,
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
        detail = _log_failure_text(str(exc), secret=secret)
        logger.warning("Frontend revalidate request failed: %s", detail)
        return {"ok": False, "error": detail}
