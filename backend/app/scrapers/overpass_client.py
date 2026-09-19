"""Shared Overpass HTTP client with retries, proxy fallback, and rate limiting."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Public mirrors — used by Render API and dev machines with open outbound HTTPS.
OVERPASS_ENDPOINTS: tuple[str, ...] = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)

_OVERPASS_SEMAPHORE = asyncio.Semaphore(1)
_RETRY_DELAYS_SEC: tuple[float, ...] = (0.0, 2.0, 5.0)


def _internal_secret() -> str:
    return (get_settings().revalidate_secret or "").strip()


async def _post_direct(
    query: str,
    *,
    timeout: float,
    log_label: str,
) -> list[dict[str, Any]]:
    last_exc: Exception | None = None
    for attempt, delay in enumerate(_RETRY_DELAYS_SEC):
        if delay:
            await asyncio.sleep(delay)
        async with httpx.AsyncClient(timeout=timeout) as client:
            for endpoint in OVERPASS_ENDPOINTS:
                try:
                    response = await client.post(endpoint, data={"data": query})
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

    try:
        async with httpx.AsyncClient(timeout=timeout + 15.0) as client:
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
