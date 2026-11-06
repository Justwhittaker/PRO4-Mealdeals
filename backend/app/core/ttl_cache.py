"""Tiny in-process TTL cache for hot read endpoints.

One API process only. A miss on another worker still hits Postgres, then
that worker caches its own copy. That is enough to collapse a crawler
burst of identical reads without adding Redis.

Entries are capped. A crawler walking random deal ids cannot grow the
process without bound; the least recently used entry is dropped.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, TypeVar

T = TypeVar("T")


class TtlCache(Generic[T]):
    def __init__(self, ttl_seconds: float, max_entries: int = 256) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_entries < 1:
            raise ValueError("max_entries must be positive")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        hit = self._entries.get(key)
        if hit is None:
            return None
        stored_at, value = hit
        if time.monotonic() - stored_at >= self.ttl_seconds:
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        if key in self._entries:
            self._entries.move_to_end(key)
        self._entries[key] = (time.monotonic(), value)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
