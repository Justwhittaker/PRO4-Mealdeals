"""Redis-backed per-cycle zone scrape stats for ntfy digests."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

from app.core.config import get_settings
from app.scrapers.zones import ZONE_CYCLE_BASE_HOURS, ZONE_ORDER

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "mealdeals:scrape_cycle"
_REDIS_TTL_SECONDS = 60 * 60 * 36  # keep ~1.5 days for late digests


def _client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def cycle_start_for_time(now: datetime | None = None) -> datetime:
    """Most recent twice-daily cycle start (06:00 or 18:00 UTC) at or before now."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    bases = sorted(ZONE_CYCLE_BASE_HOURS)
    for base in reversed(bases):
        candidate = current.replace(hour=base, minute=0, second=0, microsecond=0)
        if candidate <= current:
            return candidate
    # Before first base hour today → previous day's last base
    yesterday = current - timedelta(days=1)
    return yesterday.replace(hour=bases[-1], minute=0, second=0, microsecond=0)


def cycle_id_for_start(start: datetime) -> str:
    return start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def digest_cycle_start(now: datetime | None = None) -> datetime:
    """
    Cycle the digest should summarize.

    Digests fire at 05:50 (covers prior 18:00 cycle) and 17:50 (covers 06:00 cycle).
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    if current.hour < 12:
        prior = current - timedelta(days=1)
        return prior.replace(hour=18, minute=0, second=0, microsecond=0)
    return current.replace(hour=6, minute=0, second=0, microsecond=0)


def _zone_key(cycle_id: str, zone_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{cycle_id}:zone:{zone_id}"


def record_zone_result(zone_id: str, payload: dict[str, Any]) -> str:
    """Persist one zone's scrape outcome for the active cycle. Returns cycle_id."""
    start = cycle_start_for_time()
    cycle_id = cycle_id_for_start(start)
    zone = zone_id.strip().lower()
    body = {
        **payload,
        "zone": zone,
        "cycle_id": cycle_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client = _client()
        client.setex(_zone_key(cycle_id, zone), _REDIS_TTL_SECONDS, json.dumps(body))
    except Exception:
        logger.exception("Failed to record scrape cycle stats for %s", zone)
    return cycle_id


def load_cycle_zone_results(cycle_id: str) -> dict[str, dict[str, Any]]:
    """Return {zone_id: payload} for zones that recorded results."""
    out: dict[str, dict[str, Any]] = {}
    try:
        client = _client()
        for zone in ZONE_ORDER:
            raw = client.get(_zone_key(cycle_id, zone))
            if not raw:
                continue
            try:
                out[zone] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Corrupt cycle stats for %s/%s", cycle_id, zone)
    except Exception:
        logger.exception("Failed to load scrape cycle stats for %s", cycle_id)
    return out
