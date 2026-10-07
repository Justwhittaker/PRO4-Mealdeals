"""Skip repeat work against dead, parked, or already-missed hosts.

Guessed paths such as ``/deals`` and ``/offers`` are most of the scraper's
speculative HTTP. Domains that fail DNS or TLS, and pages that 404/403, are
remembered for the rest of the zone and (best-effort) in Redis so the next
cycle does not pay the timeout again. A real 200 offer page is never cached
as a miss.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import redis

from app.core.redis_url import redis_from_url
from app.scrapers.url_safety import safe_netloc

logger = logging.getLogger(__name__)

_MISS_STATUSES = frozenset({403, 404, 410, 451})
_DEAD_TTL_SECONDS = 7 * 24 * 60 * 60
_MISS_TTL_SECONDS = 36 * 60 * 60
_KEY_PREFIX = "mealdeals:fetch_guard"

_DEAD_NEEDLES = (
    "name or service not known",
    "nodename nor servname",
    "temporary failure in name resolution",
    "no address associated with hostname",
    "getaddrinfo",
    "name resolution",
    "errno -2",
    "errno -3",
    "certificate verify failed",
    "certificate_verify_failed",
    "sslcertverificationerror",
    "certificate has expired",
    "hostname mismatch",
    "wrong version number",
    "[ssl:",
    "sslerror",
    "tlsv1 alert",
)

_PARKED_RE = re.compile(
    r"(?i)("
    r"domain(?:\s+name)?\s+is\s+(?:for\s+sale|parked)"
    r"|this\s+domain\s+(?:may\s+be\s+)?for\s+sale"
    r"|buy\s+this\s+domain"
    r"|domain\s+parking"
    r"|this\s+(?:web\s*)?page\s+is\s+parked"
    r"|parked\s+free"
    r"|sedoparking"
    r"|hugedomains"
    r"|godaddy\s+(?:domain\s+)?auction"
    r"|afternic\.com"
    r"|dan\.com/buy"
    r")"
)


def _exception_text(exc: BaseException) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    for _ in range(6):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        parts.append(type(current).__name__)
        parts.append(str(current))
        current = current.__cause__ or current.__context__
    return " ".join(parts).lower()


def is_dead_transport_error(exc: BaseException) -> bool:
    """True for DNS failures and TLS handshake failures, not HTTP 4xx/5xx."""
    text = _exception_text(exc)
    return any(needle in text for needle in _DEAD_NEEDLES)


def looks_parked_html(html: str) -> bool:
    if not html:
        return False
    sample = html[:20000]
    return _PARKED_RE.search(sample) is not None


def _status_code(exc: BaseException) -> int | None:
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if isinstance(status, int):
        return status
    return None


def _netloc(url: str) -> str:
    return safe_netloc(url).lower()


def _miss_member(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    path = parsed.path or "/"
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


class SpeculativeFetchGuard:
    """In-process cache with an optional Redis backing store.

    ``redis_url=None`` keeps the guard process-local (tests, Redis outages).
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or ""
        self._client: redis.Redis | None = None
        self._redis_disabled = not self._redis_url
        self._dead: set[str] = set()
        self._parked: set[str] = set()
        self._misses: set[tuple[str, str]] = set()
        self._hydrated: set[str] = set()

    def should_skip(self, url: str, *, speculative: bool) -> str | None:
        """Return a reason to skip this fetch, or None to go ahead.

        Dead and parked hosts are skipped for every URL. Cached 404/403 misses
        are skipped only for speculative guessed paths, so a configured offer
        URL is still requested.
        """
        netloc = _netloc(url)
        if not netloc:
            return None
        self._hydrate(netloc)
        if netloc in self._dead:
            return "dns_or_ssl"
        if netloc in self._parked:
            return "parked"
        if speculative and (netloc, _miss_member(url)) in self._misses:
            return "cached_miss"
        return None

    def note_error(self, url: str, exc: BaseException, *, speculative: bool) -> bool:
        """Record a failed fetch. True when the host should not be probed again."""
        netloc = _netloc(url)
        if not netloc:
            return False
        self._hydrate(netloc)
        if is_dead_transport_error(exc):
            self._mark_dead(netloc)
            return True
        status = _status_code(exc)
        if speculative and status in _MISS_STATUSES:
            self._mark_miss(netloc, _miss_member(url))
        return False

    def note_html(self, url: str, html: str) -> bool:
        """Record a parked page. True when the host should not be probed again."""
        if not looks_parked_html(html):
            return False
        netloc = _netloc(url)
        if not netloc:
            return False
        self._hydrate(netloc)
        self._mark_parked(netloc)
        return True

    def _mark_dead(self, netloc: str) -> None:
        self._dead.add(netloc)
        client = self._redis()
        if client is None:
            return
        try:
            client.setex(f"{_KEY_PREFIX}:dead:{netloc}", _DEAD_TTL_SECONDS, "1")
        except Exception:  # noqa: BLE001 — cache must not break the scrape
            self._disable_redis()

    def _mark_parked(self, netloc: str) -> None:
        self._parked.add(netloc)
        client = self._redis()
        if client is None:
            return
        try:
            client.setex(f"{_KEY_PREFIX}:parked:{netloc}", _DEAD_TTL_SECONDS, "1")
        except Exception:  # noqa: BLE001
            self._disable_redis()

    def _mark_miss(self, netloc: str, member: str) -> None:
        self._misses.add((netloc, member))
        client = self._redis()
        if client is None:
            return
        key = f"{_KEY_PREFIX}:miss:{netloc}"
        try:
            client.sadd(key, member)
            client.expire(key, _MISS_TTL_SECONDS)
        except Exception:  # noqa: BLE001
            self._disable_redis()

    def _hydrate(self, netloc: str) -> None:
        if netloc in self._hydrated:
            return
        self._hydrated.add(netloc)
        client = self._redis()
        if client is None:
            return
        try:
            if client.exists(f"{_KEY_PREFIX}:dead:{netloc}"):
                self._dead.add(netloc)
            if client.exists(f"{_KEY_PREFIX}:parked:{netloc}"):
                self._parked.add(netloc)
            members = client.smembers(f"{_KEY_PREFIX}:miss:{netloc}")
            for member in members or []:
                self._misses.add((netloc, str(member)))
        except Exception:  # noqa: BLE001
            self._disable_redis()

    def _redis(self) -> redis.Redis | None:
        if self._redis_disabled:
            return None
        if self._client is not None:
            return self._client
        try:
            client = redis_from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
            )
            client.ping()
        except Exception:  # noqa: BLE001
            logger.info("Fetch-guard Redis unavailable; using in-process cache only")
            self._disable_redis()
            return None
        self._client = client
        return client

    def _disable_redis(self) -> None:
        self._redis_disabled = True
        self._client = None
