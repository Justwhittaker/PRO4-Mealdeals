"""Shared Overpass HTTP client with retries, proxy fallback, and rate limiting."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Public mirrors — used by Render API and dev machines with open outbound HTTPS.
# openstreetmap.fr first: fast and reliable; de fails fast when blocked.
# kumi.systems omitted — often hangs 60s+ with no response.
OVERPASS_ENDPOINTS: tuple[str, ...] = (
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

# NUC proxy calls must finish before client timeouts (~30s curl -m 30).
PROXY_OVERPASS_WALL_SECONDS = 22.0
PROXY_HTTP_READ_SECONDS = 12.0
NUC_PROXY_CLIENT_SECONDS = 25.0

_OVERPASS_HEADERS = {
    "User-Agent": "DineADeal/1.0 (+https://dineadeal.com; contact@dineadeal.com)",
}

_OVERPASS_SEMAPHORE = asyncio.Semaphore(1)
_RETRY_DELAYS_SEC: tuple[float, ...] = (0.0, 2.0, 5.0)
_PROXY_RETRY_DELAYS_SEC: tuple[float, ...] = (0.0,)


def _internal_secret() -> str:
    return (get_settings().revalidate_secret or "").strip()


async def _post_direct(
    query: str,
    *,
    timeout: float,
    log_label: str,
    retry_delays: tuple[float, ...] = _RETRY_DELAYS_SEC,
    read_cap: float | None = None,
) -> list[dict[str, Any]]:
    last_exc: Exception | None = None
    for attempt, delay in enumerate(retry_delays):
        if delay:
            await asyncio.sleep(delay)
        read_sec = min(max(timeout, 15.0), 90.0)
        if read_cap is not None:
            read_sec = min(read_sec, read_cap)
        http_timeout = httpx.Timeout(connect=5.0, read=read_sec, write=10.0, pool=5.0)
        async with httpx.AsyncClient(timeout=http_timeout) as client:
            for endpoint in OVERPASS_ENDPOINTS:
                try:
                    response = await client.post(
                        endpoint,
                        data={"data": query},
                        headers=_OVERPASS_HEADERS,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        return []
                    elements = payload.get("elements") or []
                    return list(elements) if isinstance(elements, list) else []
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.warning(
                        "%s failed via %s (attempt %d): %s",
                        log_label,
                        endpoint,
                        attempt + 1,
                        exc,
                    )
    if last_exc is not None:
        logger.warning("%s unavailable after retries: %s", log_label, last_exc)
    return []


async def _post_via_render_proxy(
    query: str,
    *,
    timeout: float,
    log_label: str,
) -> list[dict[str, Any]]:
    proxy_url = (get_settings().overpass_proxy_url or "").strip()
    secret = _internal_secret()
    if not proxy_url or not secret:
        logger.warning(
            "%s proxy requested but OVERPASS_PROXY_URL or REVALIDATE_SECRET unset",
            log_label,
        )
        return []

    client_timeout = min(max(timeout, 15.0), NUC_PROXY_CLIENT_SECONDS)
    try:
        async with httpx.AsyncClient(timeout=client_timeout) as client:
            response = await client.post(
                proxy_url,
                json={"query": query},
                headers={"X-Scrape-Internal-Secret": secret},
            )
            response.raise_for_status()
            payload = response.json()
            elements = payload.get("elements") or []
            return list(elements) if isinstance(elements, list) else []
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s proxy failed (%s): %s", log_label, proxy_url, exc)
        return []


async def fetch_overpass_direct(
    query: str,
    *,
    timeout: float = 55.0,
    log_label: str = "Overpass",
) -> list[dict[str, Any]]:
    """Query public Overpass mirrors (Render API / dev machines)."""
    async with _OVERPASS_SEMAPHORE:
        return await _post_direct(query, timeout=timeout, log_label=log_label)


async def fetch_overpass_for_proxy(
    query: str,
    *,
    log_label: str = "Overpass proxy",
) -> list[dict[str, Any]]:
    """Fast Overpass fetch for NUC proxy — must respond within ~25s."""
    async with _OVERPASS_SEMAPHORE:
        return await _post_direct(
            query,
            timeout=PROXY_HTTP_READ_SECONDS,
            log_label=log_label,
            retry_delays=_PROXY_RETRY_DELAYS_SEC,
            read_cap=PROXY_HTTP_READ_SECONDS,
        )


async def post_overpass_query(
    query: str,
    *,
    timeout: float = 55.0,
    log_label: str = "Overpass",
) -> list[dict[str, Any]]:
    """
    POST an Overpass QL query; return elements or [] after retries.

    When OVERPASS_PROXY_URL is set (NUC), routes via Render API when direct
    mirrors are blocked on the home network.
    """
    proxy_url = (get_settings().overpass_proxy_url or "").strip()
    if proxy_url:
        elements = await _post_via_render_proxy(
            query, timeout=timeout, log_label=log_label
        )
        if elements:
            return elements
        logger.info("%s falling back to direct Overpass mirrors", log_label)
    return await fetch_overpass_direct(query, timeout=timeout, log_label=log_label)
