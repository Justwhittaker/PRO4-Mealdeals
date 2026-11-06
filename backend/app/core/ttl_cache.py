"""Tiny in-process TTL cache for hot read endpoints.

One API process only. A miss on another worker still hits Postgres, then
that worker caches its own copy. That is enough to collapse a crawler
burst of identical reads without adding Redis.
"""

from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TtlCache(Generic[T]):
    def __init__(self, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        hit = self._entries.get(key)
        if hit is None:
            return None
        stored_at, value = hit
        if time.monotonic() - stored_at >= self.ttl_seconds:
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._entries.clear()
