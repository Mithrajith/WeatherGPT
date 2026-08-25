"""Async TTL cache with single-flight, shared by every upstream call.

The agent deliberately has no cache: this service owns the upstreams, so it is
the only component that knows how long each kind of data stays true. Current
observations go stale in minutes, climate normals in a day, and an active warning
must never be served stale at all.

Single-flight matters on demo day: twenty people asking the same question in the
same second produce one upstream request, not twenty.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Hashable


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, maxsize: int = 1024) -> None:
        self._data: dict[Hashable, _Entry] = {}
        self._locks: dict[Hashable, asyncio.Lock] = {}
        self._maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def _evict(self) -> None:
        if len(self._data) <= self._maxsize:
            return
        now = time.monotonic()
        for key in [k for k, e in self._data.items() if e.expires_at <= now]:
            self._data.pop(key, None)
            self._locks.pop(key, None)
        overflow = len(self._data) - self._maxsize
        if overflow > 0:
            for key, _ in sorted(self._data.items(), key=lambda kv: kv[1].expires_at)[:overflow]:
                self._data.pop(key, None)
                self._locks.pop(key, None)

    async def get_or_set(
        self, key: Hashable, ttl: int, factory: Callable[[], Awaitable[Any]]
    ) -> Any:
        entry = self._data.get(key)
        if entry and entry.expires_at > time.monotonic():
            self.hits += 1
            return entry.value

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            entry = self._data.get(key)
            if entry and entry.expires_at > time.monotonic():
                self.hits += 1
                return entry.value
            self.misses += 1
            value = await factory()
            if value is not None:
                self._data[key] = _Entry(value, time.monotonic() + ttl)
                self._evict()
            return value

    def stats(self) -> dict[str, Any]:
        total = self.hits + self.misses
        return {
            "entries": len(self._data),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 3) if total else 0.0,
        }


cache = TTLCache()
