"""Send push notifications via ntfy (NUC scrape digests / health)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_ntfy(
    title: str,
    body: str,
    *,
    priority: str = "default",
    tags: str | None = "newspaper",
) -> dict[str, Any]:
    """
    POST a notification to the configured ntfy topic.

    Returns a small status dict. Skips quietly when NTFY_TOPIC is unset.
    """
    settings = get_settings()
    topic = (settings.ntfy_topic or "").strip()
    if not topic:
        logger.info("Skipping ntfy (%s) — NTFY_TOPIC unset", title)
        return {"skipped": True, "reason": "no_topic"}

    base = (settings.ntfy_url or "https://ntfy.sh").rstrip("/")
    url = f"{base}/{topic}"
    headers: dict[str, str] = {
        "Title": title,
        "Priority": priority,
    }
    if tags:
        headers["Tags"] = tags
    token = (settings.ntfy_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, content=body.encode("utf-8"), headers=headers)
        if resp.status_code >= 400:
            logger.warning("ntfy failed (%s): %s", resp.status_code, resp.text[:300])
            return {"ok": False, "status": resp.status_code}
        return {"ok": True, "status": resp.status_code}
    except Exception as exc:
        logger.warning("ntfy request failed: %s", exc)
        return {"ok": False, "error": str(exc)}
