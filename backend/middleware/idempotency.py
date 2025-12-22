"""Idempotency middleware - Prevents duplicate POST operations.

Philosophy:
  - Idempotent operations = same result regardless of how many times called
  - POST operations (workflow dispatch) should be idempotent with Idempotency-Key
  - Prevents race conditions and duplicate processing

Architecture:
  - Client sends Idempotency-Key header with POST
  - Middleware caches response by key
  - Duplicate requests return cached response (409 or cached result)
  - TTL-based cache cleanup

Created: 2025-12-03
Pattern: Request Deduplication + Response Caching
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from backend.src.fi_common.logging.logger import get_logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class CachedResponse:
    """Cached idempotent response"""

    status_code: int
    headers: dict[str, str]
    body: bytes
    created_at: float
    ttl_seconds: int = 3600  # 1 hour default

    def is_expired(self) -> bool:
        """Check if cached response expired"""
        return (time.time() - self.created_at) > self.ttl_seconds


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IDEMPOTENCY STORE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class IdempotencyStore:
    """
    Thread-safe in-memory idempotency store.

    Stores responses keyed by idempotency key for duplicate detection.

    Future: Replace with Redis for distributed deployments.
    """

    def __init__(self, default_ttl: int = 3600):
        self.logger = get_logger(__name__)
        self._cache: dict[str, CachedResponse] = {}
        self._locks: dict[str, threading.RLock] = defaultdict(threading.RLock)
        self._global_lock = threading.RLock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> CachedResponse | None:
        """Get cached response if exists and not expired"""
        with self._global_lock:
            if key not in self._cache:
                return None

            cached = self._cache[key]
            if cached.is_expired():
                self.logger.info("IDEMPOTENCY_CACHE_EXPIRED", key=key)
                del self._cache[key]
                return None

            self.logger.info("IDEMPOTENCY_CACHE_HIT", key=key)
            return cached

    def set(
        self,
        key: str,
        status_code: int,
        headers: dict[str, str],
        body: bytes,
        ttl: int | None = None,
    ) -> None:
        """Cache response for idempotency key"""
        ttl = ttl or self._default_ttl

        with self._global_lock:
            self._cache[key] = CachedResponse(
                status_code=status_code,
                headers=headers,
                body=body,
                created_at=time.time(),
                ttl_seconds=ttl,
            )

        self.logger.info("IDEMPOTENCY_CACHE_SET", key=key, ttl=ttl)

    def acquire_lock(self, key: str) -> threading.RLock:
        """Get lock for idempotency key (for concurrent requests with same key)"""
        with self._global_lock:
            return self._locks[key]

    def cleanup_expired(self) -> int:
        """Remove expired entries (call periodically)"""
        with self._global_lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]

        self.logger.debug("IDEMPOTENCY_CLEANUP", expired_count=len(expired_keys))
        return len(expired_keys)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIDDLEWARE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for idempotent POST operations.

    Usage:
        app.add_middleware(IdempotencyMiddleware, paths=["/api/workflows/"])

    Client must send:
        Idempotency-Key: <uuid or unique string>

    Behavior:
        - First request: Process normally, cache response
        - Duplicate request: Return cached response (or 409 if in-progress)
        - Missing key: Allow request (optional enforcement)

    Config:
        - paths: List of path prefixes to enforce idempotency
        - require_key: If True, reject POST without Idempotency-Key
        - ttl: Cache TTL in seconds (default 1 hour)
    """

    def __init__(
        self,
        app,
        paths: list[str] | None = None,
        require_key: bool = False,
        ttl: int = 3600,
    ):
        super().__init__(app)
        self.paths = paths or ["/api/workflows/"]
        self.require_key = require_key
        self.ttl = ttl
        self.store = IdempotencyStore(default_ttl=ttl)
        self.logger = get_logger(__name__)

    async def dispatch(self, request: Request, call_next):
        """Process request with idempotency check"""

        # Only check POST requests on configured paths
        if request.method != "POST":
            return await call_next(request)

        if not any(request.url.path.startswith(path) for path in self.paths):
            return await call_next(request)

        # Get idempotency key
        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key:
            if self.require_key:
                self.logger.warning(
                    "IDEMPOTENCY_KEY_MISSING",
                    path=request.url.path,
                    method=request.method,
                )
                return JSONResponse(
                    status_code=400,
                    content={"error": "Idempotency-Key header required for POST operations"},
                )
            else:
                # Allow request without key (non-enforced mode)
                return await call_next(request)

        # Normalize key (hash if too long)
        if len(idempotency_key) > 128:
            idempotency_key = hashlib.sha256(idempotency_key.encode()).hexdigest()

        self.logger.info(
            "IDEMPOTENCY_CHECK",
            key=idempotency_key,
            path=request.url.path,
        )

        # Check cache
        cached = self.store.get(idempotency_key)
        if cached:
            self.logger.info(
                "IDEMPOTENCY_DUPLICATE_REQUEST",
                key=idempotency_key,
                cached_status=cached.status_code,
            )
            return Response(
                content=cached.body,
                status_code=cached.status_code,
                headers=cached.headers,
            )

        # Acquire lock for this key (prevents concurrent processing of same request)
        lock = self.store.acquire_lock(idempotency_key)

        with lock:
            # Double-check cache (another thread might have completed while we waited)
            cached = self.store.get(idempotency_key)
            if cached:
                return Response(
                    content=cached.body,
                    status_code=cached.status_code,
                    headers=cached.headers,
                )

            # Process request
            response = await call_next(request)

            # Cache successful responses (2xx, 4xx but not 5xx)
            # 5xx errors are transient, should be retried
            if 200 <= response.status_code < 500:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                # Extract headers
                headers = dict(response.headers)

                # Cache response
                self.store.set(
                    key=idempotency_key,
                    status_code=response.status_code,
                    headers=headers,
                    body=body,
                    ttl=self.ttl,
                )

                # Return response with body
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=headers,
                )

            return response


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_idempotency_key(session_id: str, operation: str) -> str:
    """
    Generate deterministic idempotency key.

    Useful for internal operations that need idempotency.

    Args:
        session_id: Session identifier
        operation: Operation type (e.g., "diarization", "soap")

    Returns:
        SHA-256 hash suitable for Idempotency-Key header
    """
    data = f"{session_id}:{operation}:{datetime.now(UTC).date().isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()
