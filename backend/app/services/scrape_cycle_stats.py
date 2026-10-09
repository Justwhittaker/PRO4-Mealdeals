"""Redis-backed per-cycle zone scrape stats for ntfy digests."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

from app.core.config import get_settings
from app.core.task_errors import reraise_if_fatal
from app.core.redis_url import redis_from_url
from app.scrapers.zones import ZONE_CYCLE_BASE_HOURS

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "mealdeals:scrape_cycle"
_REDIS_TTL_SECONDS = 60 * 60 * 36  # keep ~1.5 days for late digests


def _client() -> redis.Redis:
    settings = get_settings()
    return redis_from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


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


def cycle_id_from_task_request(request: Any) -> str | None:
    """Read the cycle id stamped onto the message when it was queued."""
    if request is None:
        return None
    direct = getattr(request, "scrape_cycle_id", None)
    if direct:
        return str(direct)
    headers = getattr(request, "headers", None)
    if isinstance(headers, dict):
        stamped = headers.get("scrape_cycle_id")
        if stamped:
            return str(stamped)
    return None


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


def zone_already_succeeded(cycle_id: str, zone_id: str) -> bool:
    """True when this cycle already stored a finished successful zone result.

    A ``running`` marker is not success, so a crash retry still does the work.
    Redis failures return False so a stats outage does not skip the scrape.
    """
    zone = zone_id.strip().lower()
    try:
        raw = _client().get(_zone_key(cycle_id, zone))
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to read scrape cycle stats for %s/%s", cycle_id, zone)
        return False
    if not raw:
        return False
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if str(payload.get("status") or "") == "running":
        return False
    return payload.get("ok") is True and not payload.get("error")


def record_zone_result(
    zone_id: str,
    payload: dict[str, Any],
    *,
    cycle_id: str | None = None,
) -> str:
    """Persist one zone's scrape outcome. Returns the cycle_id used.

    Pass the cycle id stamped when the task was queued. Falling back to "now"
    attributes a late finish to whichever cycle is current at completion.
    """
    if not cycle_id:
        cycle_id = cycle_id_for_start(cycle_start_for_time())
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
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to record scrape cycle stats for %s", zone)
    return cycle_id


def _zone_set_key(cycle_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{cycle_id}:zone_set"


def remember_cycle_zone_set(cycle_id: str, zones: list[str]) -> None:
    """Remember the zone ids a cycle was scheduled with.

    ``SET NX`` keeps the first publisher's list. A later deploy that changes
    ``ZONE_ORDER`` must not overwrite the set already queued for this cycle.
    """
    names = [str(zone).strip().lower() for zone in zones if str(zone).strip()]
    try:
        _client().set(
            _zone_set_key(cycle_id),
            json.dumps(names),
            nx=True,
            ex=_REDIS_TTL_SECONDS,
        )
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to record scrape cycle zone set for %s", cycle_id)


def load_cycle_zone_set(cycle_id: str) -> list[str] | None:
    """Zone ids stamped when this cycle was queued, if that record exists."""
    try:
        raw = _client().get(_zone_set_key(cycle_id))
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to read scrape cycle zone set for %s", cycle_id)
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Corrupt cycle zone set for %s", cycle_id)
        return None
    if not isinstance(payload, list):
        return None
    names = [str(zone).strip().lower() for zone in payload if str(zone).strip()]
    return names or None


def load_cycle_zone_results(cycle_id: str) -> dict[str, dict[str, Any]]:
    """Return {zone_id: payload} for every zone that recorded a result.

    The scan includes retired names. A cycle queued under an older set still
    has those keys after ``ZONE_ORDER`` changes.
    """
    out: dict[str, dict[str, Any]] = {}
    pattern = f"{_REDIS_KEY_PREFIX}:{cycle_id}:zone:*"
    marker = ":zone:"
    try:
        client = _client()
        for key in client.scan_iter(match=pattern):
            raw = client.get(key)
            if not raw:
                continue
            key_text = str(key)
            fallback = (
                key_text.rsplit(marker, 1)[-1].strip().lower()
                if marker in key_text
                else ""
            )
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(
                    "Corrupt cycle stats for %s/%s",
                    cycle_id,
                    fallback or key_text,
                )
                continue
            if not isinstance(payload, dict):
                continue
            zone = str(payload.get("zone") or fallback).strip().lower()
            if not zone:
                continue
            out[zone] = payload
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to load scrape cycle stats for %s", cycle_id)
    return out


def _city_retry_key(cycle_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}:{cycle_id}:city_retries"


def _city_retry_field(country: str, city: str) -> str:
    return f"{country.strip().upper()}\t{city.strip()}"


def claim_city_retries(
    cycle_id: str,
    cities: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Claim each city once for this cycle. Already-claimed cities are skipped.

    ``HSETNX`` is the guard against a second digest, a restart, or a duplicate
    trigger. A city that loses the claim is not queued again.
    """
    claimed: list[tuple[str, str]] = []
    if not cities:
        return claimed
    try:
        client = _client()
        key = _city_retry_key(cycle_id)
        now = datetime.now(timezone.utc).isoformat()
        for country, city in cities:
            code = country.strip().upper()
            name = city.strip()
            if not code or not name:
                continue
            payload = json.dumps(
                {
                    "status": "queued",
                    "country": code,
                    "city": name,
                    "queued_at": now,
                }
            )
            if client.hsetnx(key, _city_retry_field(code, name), payload):
                claimed.append((code, name))
        if claimed:
            client.expire(key, _REDIS_TTL_SECONDS)
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to claim city retries for %s", cycle_id)
    return claimed


def begin_city_retry(cycle_id: str, country: str, city: str) -> bool:
    """Move one claimed city from queued to running.

    A second worker, a redelivery, or a repeat call leaves the city alone.
    """
    code = country.strip().upper()
    name = city.strip()
    key = _city_retry_key(cycle_id)
    field = _city_retry_field(code, name)
    lock = f"{key}:lock:{field}"
    try:
        client = _client()
        if not client.set(lock, "1", nx=True, ex=_REDIS_TTL_SECONDS):
            return False
        raw = client.hget(key, field)
        if not raw:
            return False
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("status") != "queued":
            return False
        payload["status"] = "running"
        client.hset(key, field, json.dumps(payload))
        return True
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception(
            "Failed to begin city retry %s/%s for %s",
            code,
            name,
            cycle_id,
        )
        return False


def record_city_retry_outcome(
    cycle_id: str,
    country: str,
    city: str,
    *,
    ok: bool,
    error: str | None = None,
) -> None:
    """Store the single retry result. Failed cities stay failed for the next cycle."""
    code = country.strip().upper()
    name = city.strip()
    payload = {
        "status": "recovered" if ok else "failed",
        "country": code,
        "city": name,
        "error": (error or "")[:500],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client = _client()
        key = _city_retry_key(cycle_id)
        client.hset(key, _city_retry_field(code, name), json.dumps(payload))
        client.expire(key, _REDIS_TTL_SECONDS)
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception(
            "Failed to record city retry %s/%s for %s",
            code,
            name,
            cycle_id,
        )


def load_city_retries(cycle_id: str) -> list[dict[str, Any]]:
    """Retry rows for a cycle, ordered by country then city."""
    try:
        raw_map = _client().hgetall(_city_retry_key(cycle_id))
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to load city retries for %s", cycle_id)
        return []
    if not raw_map:
        return []
    items: list[dict[str, Any]] = []
    for raw in raw_map.values():
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Corrupt city retry row for %s", cycle_id)
            continue
        if isinstance(payload, dict):
            items.append(payload)
    items.sort(
        key=lambda item: (
            str(item.get("country") or ""),
            str(item.get("city") or ""),
        )
    )
    return items


def claim_city_retry_followup(cycle_id: str) -> bool:
    """True the first time this cycle's retry follow-up is claimed."""
    key = f"{_REDIS_KEY_PREFIX}:{cycle_id}:city_retry_followup"
    try:
        return bool(_client().set(key, "1", nx=True, ex=_REDIS_TTL_SECONDS))
    except Exception as exc:
        reraise_if_fatal(exc)
        logger.exception("Failed to claim city retry follow-up for %s", cycle_id)
        return False
