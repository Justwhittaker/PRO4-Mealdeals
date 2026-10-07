"""Skip repeat work against dead, parked, or already-missed hosts.

Guessed paths such as ``/deals`` and ``/offers`` are most of the scraper's
speculative HTTP. A host is remembered as dead or parked only after repeated
failures, and only for a few hours. Any later successful fetch, including the
configured page itself, clears that mark. A single DNS or TLS blip still stops
the rest of the current probe burst, but it does not hide the merchant from
the next city. A real 200 offer page is never cached as a miss.
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import redis

from app.core.redis_url import redis_from_url
from app.core.task_errors import reraise_if_fatal
from app.scrapers.url_safety import safe_netloc

logger = logging.getLogger(__name__)

_MISS_STATUSES = frozenset({403, 404, 410, 451})
# One blip must not hide a merchant for a week. Three transport failures, or
# two parked pages, skip guessed paths for a few hours. The next cycle retries.
TRANSPORT_FAILURES_BEFORE_SKIP = 3
PARKED_OBSERVATIONS_BEFORE_SKIP = 2
HOST_SKIP_TTL_SECONDS = 6 * 60 * 60
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
        self._strikes: dict[tuple[str, str], int] = {}
        self._misses: set[tuple[str, str]] = set()
        self._hydrated: set[str] = set()

    def should_skip(self, url: str, *, speculative: bool) -> str | None:
        """Return a reason to skip this fetch, or None to go ahead.

        A dead or parked host skips guessed paths only. The configured page is
        still requested so a later success can clear the mark. Cached 404/403
        misses are also speculative-only.
        """
        netloc = _netloc(url)
        if not netloc:
            return None
        self._hydrate(netloc)
        if speculative and netloc in self._dead:
            return "dns_or_ssl"
        if speculative and netloc in self._parked:
            return "parked"
        if speculative and (netloc, _miss_member(url)) in self._misses:
            return "cached_miss"
        return None

    def note_error(self, url: str, exc: BaseException, *, speculative: bool) -> bool:
        """Record a failed fetch.

        True means stop the rest of this host's probe burst. DNS and TLS
        failures always do that (the next guessed path will fail the same way).
        The host is skipped on later calls only after repeated failures.
        """
        reraise_if_fatal(exc)
        netloc = _netloc(url)
        if not netloc:
            return False
        self._hydrate(netloc)
        if is_dead_transport_error(exc):
            count = self._bump_strike("dead", netloc)
            if count >= TRANSPORT_FAILURES_BEFORE_SKIP:
                self._mark_dead(netloc)
            return True
        status = _status_code(exc)
        if speculative and status in _MISS_STATUSES:
            self._mark_miss(netloc, _miss_member(url))
        return False

    def note_html(self, url: str, html: str) -> bool:
        """Record a parked page. True when guessed paths on this host should stop."""
        if not looks_parked_html(html):
            return False
        netloc = _netloc(url)
        if not netloc:
            return False
        self._hydrate(netloc)
        count = self._bump_strike("parked", netloc)
        if count < PARKED_OBSERVATIONS_BEFORE_SKIP:
            return False
        self._mark_parked(netloc)
        return True

    def note_success(self, url: str, *, html: str | None = None) -> None:
        """A completed fetch. Clears a dead or parked mark earned by a blip.

        Transport success always clears a DNS/TLS mark. A body that is not a
        parking page also clears a parked mark. The configured page goes through
        here, so one later 200 undoes a skip without waiting out the TTL.
        """
        netloc = _netloc(url)
        if not netloc:
            return
        self._hydrate(netloc)
        self._clear_kind(netloc, "dead")
        if html is None or not looks_parked_html(html):
            self._clear_kind(netloc, "parked")

    def _bump_strike(self, kind: str, netloc: str) -> int:
        client = self._redis()
        if client is not None:
            key = f"{_KEY_PREFIX}:{kind}_strikes:{netloc}"
            try:
                count = int(client.incr(key))
                if count == 1:
                    client.expire(key, HOST_SKIP_TTL_SECONDS)
            except Exception as exc:  # noqa: BLE001 — cache must not break the scrape
                reraise_if_fatal(exc)
                self._disable_redis()
            else:
                self._strikes[(kind, netloc)] = count
                return count
        count = self._strikes.get((kind, netloc), 0) + 1
        self._strikes[(kind, netloc)] = count
        return count

    def _mark_dead(self, netloc: str) -> None:
        self._dead.add(netloc)
        self._remember(f"{_KEY_PREFIX}:dead:{netloc}")

    def _mark_parked(self, netloc: str) -> None:
        self._parked.add(netloc)
        self._remember(f"{_KEY_PREFIX}:parked:{netloc}")

    def _remember(self, key: str) -> None:
        client = self._redis()
        if client is None:
            return
        try:
            client.setex(key, HOST_SKIP_TTL_SECONDS, "1")
        except Exception as exc:  # noqa: BLE001 — cache must not break the scrape
            reraise_if_fatal(exc)
            self._disable_redis()

    def _clear_kind(self, netloc: str, kind: str) -> None:
        if kind == "dead":
            self._dead.discard(netloc)
        elif kind == "parked":
            self._parked.discard(netloc)
        else:
            raise ValueError(f"Unknown fetch-guard kind: {kind}")
        self._strikes.pop((kind, netloc), None)
        client = self._redis()
        if client is None:
            return
        try:
            client.delete(
                f"{_KEY_PREFIX}:{kind}:{netloc}",
                f"{_KEY_PREFIX}:{kind}_strikes:{netloc}",
            )
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
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
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
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
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
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
        except Exception as exc:  # noqa: BLE001
            reraise_if_fatal(exc)
            logger.info("Fetch-guard Redis unavailable; using in-process cache only")
            self._disable_redis()
            return None
        self._client = client
        return client

    def _disable_redis(self) -> None:
        self._redis_disabled = True
        self._client = None
