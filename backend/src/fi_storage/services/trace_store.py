from __future__ import annotations

import time
from threading import Lock
from typing import Any


class TraceStore:
    """In-memory trace store with TTL. Not for production persistent use.

    Stores entries keyed by request_id (UUID) with trace metadata.
    """

    def __init__(self, ttl_s: int = 600):
        self._ttl = ttl_s
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = Lock()

    def put(self, request_id: str, trace: dict[str, Any]) -> None:
        with self._lock:
            self._store[request_id] = (time.time(), trace)

    def get(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._store.get(request_id)
            if not item:
                return None
            ts, trace = item
            if time.time() - ts > self._ttl:
                # expired
                del self._store[request_id]
                return None
            return trace

    def cleanup(self) -> None:
        with self._lock:
            now = time.time()
            expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
            for k in expired:
                del self._store[k]


# Singleton
_TRACE_STORE: TraceStore | None = None


def get_trace_store(ttl_s: int | None = None) -> TraceStore:
    global _TRACE_STORE
    if _TRACE_STORE is None:
        _TRACE_STORE = TraceStore(ttl_s or 600)
    return _TRACE_STORE
