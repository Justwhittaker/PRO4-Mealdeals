"""Overpass queries that survive a dead mirror.

Public interpreters (overpass-api.de and the usual mirrors) refuse or time
out together some days. This client rotates the list, backs off, and returns
a failure instead of raising, so one bad tile does not abort the week.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.scrapers.overpass_client import OVERPASS_ENDPOINTS, _post_via_render_proxy
from app.scrapers.politeness import pace_overpass, penalize_overpass

logger = logging.getLogger(__name__)

# de and fr are the ones the deal scraper already trusts. kumi and private.coffee
# are extra free mirrors. Each attempt uses a short read timeout so a hung
# mirror cannot run into the 07:00 zone scrapes.
OVERPASS_MIRRORS: tuple[str, ...] = OVERPASS_ENDPOINTS + (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

_HEADERS = {
    "User-Agent": "DineADeal/1.0 (+https://dineadeal.com; contact@dineadeal.com)",
}
_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 8.0)

Poster = Callable[[str, str, float], Awaitable[list[dict[str, Any]]]]
Sleeper = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class OverpassOutcome:
    ok: bool
    elements: list[dict[str, Any]]
    error: str | None
    endpoint: str | None
    attempts: int
    timed_out: bool = False


async def _post(endpoint: str, query: str, timeout: float) -> list[dict[str, Any]]:
    await pace_overpass()
    http_timeout = httpx.Timeout(connect=5.0, read=timeout, write=10.0, pool=5.0)
    async with httpx.AsyncClient(timeout=http_timeout) as client:
        response = await client.post(
            endpoint,
            data={"data": query},
            headers=_HEADERS,
        )
        if response.status_code == 429:
            penalize_overpass()
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        return []
    elements = payload.get("elements") or []
    return list(elements) if isinstance(elements, list) else []


def _rotated(mirrors: tuple[str, ...], start: int) -> tuple[str, ...]:
    if not mirrors:
        return ()
    index = start % len(mirrors)
    return mirrors[index:] + mirrors[:index]


async def query_overpass(
    query: str,
    *,
    mirrors: tuple[str, ...] = OVERPASS_MIRRORS,
    start: int = 0,
    timeout: float = 25.0,
    rounds: int = 2,
    post: Poster | None = None,
    sleep: Sleeper | None = None,
) -> OverpassOutcome:
    """Try every mirror, then one more round after a longer backoff.

    HTTP 200 with an empty element list is success: that bbox has no matches.
    A failure means every attempt raised or returned a non-2xx status.
    """
    poster = post or _post
    pause = sleep or asyncio.sleep
    proxy_url = (get_settings().overpass_proxy_url or "").strip()
    if proxy_url and post is None:
        try:
            proxied = await _post_via_render_proxy(
                query,
                timeout=timeout,
                log_label="New Business Outreach",
            )
        except Exception as exc:  # noqa: BLE001 — fall through to the public mirrors
            reraise_if_fatal(exc)
            logger.warning("New Business Outreach proxy failed: %s", exc)
            proxied = []
        if proxied:
            return OverpassOutcome(True, proxied, None, proxy_url, 1, False)
        logger.info("New Business Outreach proxy empty, trying public mirrors")
    order = _rotated(mirrors, start)
    if not order:
        return OverpassOutcome(False, [], "no mirrors", None, 0, False)

    attempts = 0
    timeout_failures = 0
    last_error = "unavailable"
    planned: list[str] = []
    for _round in range(max(rounds, 1)):
        planned.extend(order)
    last_index = len(planned) - 1
    for index, endpoint in enumerate(planned):
        attempts += 1
        try:
            elements = await poster(endpoint, query, timeout)
        except Exception as exc:  # noqa: BLE001 — one mirror must not abort the tile
            reraise_if_fatal(exc)
            last_error = str(exc)
            if isinstance(exc, httpx.TimeoutException) or "timeout" in last_error.lower():
                timeout_failures += 1
            logger.warning(
                "New Business Outreach Overpass failed via %s (attempt %s): %s",
                endpoint,
                attempts,
                exc,
            )
            if index != last_index:
                delay = _BACKOFF_SECONDS[min(index, len(_BACKOFF_SECONDS) - 1)]
                await pause(delay)
            continue
        return OverpassOutcome(True, elements, None, endpoint, attempts)

    logger.warning(
        "New Business Outreach Overpass unavailable after %s attempts: %s",
        attempts,
        last_error,
    )
    return OverpassOutcome(
        False,
        [],
        last_error,
        None,
        attempts,
        timed_out=timeout_failures > 0 and timeout_failures == attempts,
    )
