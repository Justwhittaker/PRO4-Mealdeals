"""Space requests so several scrape workers do not burst the same host.

The NUC runs multiple zone processes. Each one already fetches cities one at
a time, but together they share Overpass and the same chain websites. Redis
keeps a gap between those processes. An in-process clock covers Redis outages.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time

import redis

from app.core.config import get_settings
from app.core.redis_url import redis_from_url
from app.core.task_errors import reraise_if_fatal
from app.scrapers.url_safety import safe_netloc

logger = logging.getLogger(__name__)

# Half a second is enough to stop six workers stampeding one merchant.
HOST_GAP_SECONDS = 0.5
# Public Overpass mirrors 429 when several interpreters run at once.
OVERPASS_GAP_SECONDS = 2.0
RATE_LIMIT_BACKOFF_SECONDS = 45.0
_KEY_PREFIX = "mealdeals:polite:"

_lock = threading.Lock()
_next_monotonic: dict[str, float] = {}
_redis_client: redis.Redis | None = None
_redis_disabled = False


def host_bucket(url: str) -> str:
    host = safe_netloc(url).lower()
    if host.startswith("www."):
        host = host[4:]
    return f"host:{host}" if host else "host:unknown"


def _redis() -> redis.Redis | None:
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        client = redis_from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
        client.ping()
    except Exception as exc:  # noqa: BLE001 — pacing must not abort a scrape
        reraise_if_fatal(exc)
        logger.info("Politeness Redis unavailable; pacing inside this process only")
        _redis_disabled = True
        return None
    _redis_client = client
    return client


def _disable_redis() -> None:
    global _redis_client, _redis_disabled
    _redis_disabled = True
    _redis_client = None


def _redis_wait(bucket: str, gap_seconds: float) -> float:
    """Return how long Redis says to wait. 0 means this caller owns the slot."""
    client = _redis()
    if client is None:
        return 0.0
    key = f"{_KEY_PREFIX}{bucket}"
    px = max(1, int(gap_seconds * 1000))
    try:
        if client.set(key, "1", nx=True, px=px):
            return 0.0
        ttl_ms = int(client.pttl(key))
    except Exception as exc:  # noqa: BLE001
        reraise_if_fatal(exc)
        logger.info("Politeness Redis failed; pacing inside this process only")
        _disable_redis()
        return 0.0
    if ttl_ms < 0:
        return 0.0
    return ttl_ms / 1000.0


def reserve_slot(bucket: str, gap_seconds: float) -> float:
    """Claim the next turn for ``bucket`` and return how long to sleep first."""
    now = time.monotonic()
    with _lock:
        local_wait = max(0.0, _next_monotonic.get(bucket, 0.0) - now)
        _next_monotonic[bucket] = now + local_wait + gap_seconds
    remote_wait = _redis_wait(bucket, gap_seconds)
    if remote_wait > local_wait:
        with _lock:
            _next_monotonic[bucket] = time.monotonic() + remote_wait + gap_seconds
    return max(local_wait, remote_wait)


def penalize(bucket: str, seconds: float = RATE_LIMIT_BACKOFF_SECONDS) -> None:
    """Hold a bucket after HTTP 429 so the next caller waits it out."""
    now = time.monotonic()
    with _lock:
        _next_monotonic[bucket] = max(_next_monotonic.get(bucket, 0.0), now + seconds)
    client = _redis()
    if client is None:
        return
    try:
        client.set(f"{_KEY_PREFIX}{bucket}", "429", px=max(1, int(seconds * 1000)))
    except Exception as exc:  # noqa: BLE001
        reraise_if_fatal(exc)


async def pace(bucket: str, gap_seconds: float) -> None:
    """Sleep until ``bucket`` may be requested again.

    ``reserve_slot`` already claims the following turn, so this sleeps once.
    Sleeping and claiming again would stack gaps on top of each other.
    """
    wait = reserve_slot(bucket, gap_seconds)
    if wait > 0:
        await asyncio.sleep(wait)


async def pace_host(url: str) -> None:
    await pace(host_bucket(url), HOST_GAP_SECONDS)


async def pace_overpass() -> None:
    await pace("overpass", OVERPASS_GAP_SECONDS)


def penalize_host(url: str) -> None:
    penalize(host_bucket(url))


def penalize_overpass() -> None:
    penalize("overpass")


def pace_host_sync(url: str) -> None:
    """Blocking host gap for sync HTTP (Wikimedia placeholders)."""
    wait = reserve_slot(host_bucket(url), HOST_GAP_SECONDS)
    if wait > 0:
        time.sleep(wait)
