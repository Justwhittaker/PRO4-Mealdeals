"""Redis URL helpers that accept the Celery/Render CERT_NONE query form.

Celery's kombu broker maps ``ssl_cert_reqs=CERT_NONE`` onto ``ssl.CERT_NONE``.
redis-py's own parser only accepts ``none`` / ``optional`` / ``required`` and
raises ``RedisError: Invalid SSL Certificate Requirements Flag: CERT_NONE``.
Production ``REDIS_URL`` uses the Celery form, so the scrape-cycle stats client
must normalise it before ``from_url``.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

import redis

_CERT_REQS_ALIASES = {
    "CERT_NONE": "none",
    "NONE": "none",
    "CERT_OPTIONAL": "optional",
    "OPTIONAL": "optional",
    "CERT_REQUIRED": "required",
    "REQUIRED": "required",
}

_CERT_REQS_RE = re.compile(r"(ssl_cert_reqs=)([^&]*)", re.IGNORECASE)


def normalize_redis_url(url: str) -> str:
    """Rewrite ``ssl_cert_reqs=CERT_NONE`` (and siblings) to redis-py values.

    Leaves the rest of the URL untouched, including credentials. Values redis-py
    already accepts (``none``, ``optional``, ``required``) are unchanged.
    """
    if not url or "ssl_cert_reqs=" not in url.lower():
        return url

    def _replace(match: re.Match[str]) -> str:
        raw = unquote(match.group(2)).strip()
        mapped = _CERT_REQS_ALIASES.get(raw.upper())
        if mapped is None or mapped == raw:
            return match.group(0)
        return f"{match.group(1)}{mapped}"

    return _CERT_REQS_RE.sub(_replace, url, count=1)


def redis_from_url(url: str, **kwargs: Any) -> redis.Redis:
    """``redis.Redis.from_url`` after normalising SSL cert requirement aliases."""
    return redis.Redis.from_url(normalize_redis_url(url), **kwargs)
