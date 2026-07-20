"""The client pool: a HOT CACHE, not memory — each entry is a live `claude`
subprocess. On a small box an unbounded pool is an OOM waiting to happen, so it
is capped and evicted LRU; idle clients are reaped by age. Evicting loses
nothing: the transcript is in Postgres and the next turn rebuilds the client
with `resume=` (the whole point of the store)."""

import asyncio
import os
from typing import Any

POOL_MAX = int(os.environ.get("AIRE_POOL_MAX", "8"))
POOL_IDLE_S = float(os.environ.get("AIRE_POOL_IDLE_S", "900"))


class Pool:
    def __init__(self) -> None:
        self.clients: dict[str, Any] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.used: dict[str, float] = {}  # key → last-use monotonic ts (LRU)
        self.guard = asyncio.Lock()

    def busy(self, key: str) -> bool:
        lock = self.locks.get(key)
        return lock is not None and lock.locked()

    async def close_one(self, key: str) -> None:
        """Evict one client: close its subprocess, drop its pool/lru/lock state."""
        client = self.clients.pop(key, None)
        self.used.pop(key, None)
        self.locks.pop(key, None)
        if client is not None:
            try:
                await client.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass

    async def evict(self, now: float) -> None:
        """Reap idle clients, then LRU-trim to POOL_MAX. Never evict a client
        whose lock is held (a turn is in flight on it)."""
        for key in [k for k, t in self.used.items()
                    if now - t > POOL_IDLE_S and not self.busy(k)]:
            await self.close_one(key)
        while len(self.clients) > POOL_MAX:
            idle = sorted((t, k) for k, t in self.used.items() if not self.busy(k))
            if not idle:
                break  # everything left is mid-turn; let it be
            await self.close_one(idle[0][1])

    async def close_all(self) -> None:
        for client in self.clients.values():
            try:
                await client.__aexit__(None, None, None)
            except Exception:  # noqa: BLE001 - best-effort teardown
                pass
        self.clients.clear()
        self.locks.clear()
        self.used.clear()
