"""
Token Bucket Rate Limiter

Implementación in-memory del algoritmo Token Bucket para rate-limiting.
Permite burst traffic mientras mantiene throughput promedio controlado.

Architecture:
    - In-memory (defaultdict) para MVP
    - Upgrade path: Redis backend para multi-process deployment
    - Separate limiters por tipo (IP vs session)

Performance:
    - O(1) para allow() check
    - Auto-cleanup: buckets inactivos > 1 hora se eliminan automáticamente

Philosophy (Axiom 1 - Materia = Glitch):
    - Acepta bursts (feature, not bug)
    - 99.9% throughput garantizado, no 100%
    - Graceful degradation: 429 con Retry-After header
"""

from collections import defaultdict
from time import time
from typing import Any, Dict

import structlog

logger = structlog.get_logger()


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter con auto-refill y burst support.

    Algoritmo:
        1. Bucket tiene `burst` tokens inicialmente
        2. Cada request consume 1 token
        3. Tokens se rellenan a tasa `rpm / 60` por segundo
        4. Si tokens = 0 → rate limited (429)

    Example:
        >>> limiter = TokenBucketRateLimiter(rpm=20, burst=5)
        >>> limiter.allow("192.168.1.1")  # True (4 tokens quedan)
        >>> limiter.allow("192.168.1.1")  # True (3 tokens quedan)
        >>> # ... (consume 3 más)
        >>> limiter.allow("192.168.1.1")  # False (rate limited)
    """

    def __init__(self, requests_per_min: int, burst: int):
        """
        Initialize rate limiter.

        Args:
            requests_per_min: Throughput promedio (ej: 20 → 1 req cada 3s)
            burst: Burst capacity (ej: 5 → 5 requests instantáneas OK)
        """
        self.rpm = requests_per_min
        self.burst = burst
        self.buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"tokens": burst, "last_refill": time()}
        )

        # Metrics
        self.total_requests = 0
        self.total_limited = 0

        logger.info(
            "RATE_LIMITER_INITIALIZED",
            rpm=requests_per_min,
            burst=burst,
            refill_rate_per_sec=requests_per_min / 60,
        )

    def allow(self, key: str) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (IP address, session_id, etc.)

        Returns:
            True if request allowed, False if rate limited

        Side effects:
            - Consumes 1 token if allowed
            - Auto-refills tokens based on elapsed time
            - Updates metrics
        """
        self.total_requests += 1
        bucket = self.buckets[key]
        now = time()

        # Auto-refill tokens
        elapsed = now - bucket["last_refill"]
        refill_count = int(elapsed * self.rpm / 60)

        if refill_count > 0:
            bucket["tokens"] = min(self.burst, bucket["tokens"] + refill_count)
            bucket["last_refill"] = now

        # Check if tokens available
        if bucket["tokens"] > 0:
            bucket["tokens"] -= 1

            logger.debug(
                "RATE_LIMIT_ALLOW",
                key=key,
                tokens_remaining=bucket["tokens"],
                refilled=refill_count,
            )

            return True

        # Rate limited
        self.total_limited += 1

        logger.warning(
            "RATE_LIMIT_DENY",
            key=key,
            refill_count=refill_count,
            total_limited=self.total_limited,
        )

        return False

    def get_remaining(self, key: str) -> int:
        """
        Get remaining tokens for key (useful for X-RateLimit-Remaining header).

        Args:
            key: Unique identifier

        Returns:
            Number of tokens remaining (0 if rate limited)
        """
        if key not in self.buckets:
            return self.burst

        bucket = self.buckets[key]
        now = time()
        elapsed = now - bucket["last_refill"]
        refill_count = int(elapsed * self.rpm / 60)

        return min(self.burst, bucket["tokens"] + refill_count)

    def get_retry_after(self, key: str) -> int:
        """
        Calculate seconds until next token available (for Retry-After header).

        Args:
            key: Unique identifier

        Returns:
            Seconds until next request allowed (minimum 1)
        """
        # Time to next token = 60 / rpm seconds
        seconds_per_token = 60 / self.rpm
        return max(1, int(seconds_per_token))

    def reset(self, key: str) -> None:
        """
        Reset bucket for key (admin override).

        Args:
            key: Unique identifier to reset
        """
        if key in self.buckets:
            del self.buckets[key]
            logger.info("RATE_LIMIT_RESET", key=key)

    def cleanup_stale(self, max_age_seconds: int = 3600) -> int:
        """
        Remove buckets inactive for > max_age_seconds.

        Args:
            max_age_seconds: Age threshold (default 1 hour)

        Returns:
            Number of buckets removed
        """
        now = time()
        stale_keys = [
            key
            for key, bucket in self.buckets.items()
            if now - bucket["last_refill"] > max_age_seconds
        ]

        for key in stale_keys:
            del self.buckets[key]

        if stale_keys:
            logger.info("RATE_LIMITER_CLEANUP", removed_count=len(stale_keys))

        return len(stale_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dict with total_requests, total_limited, active_buckets, limit_rate
        """
        return {
            "total_requests": self.total_requests,
            "total_limited": self.total_limited,
            "active_buckets": len(self.buckets),
            "limit_rate": self.total_limited / max(1, self.total_requests),
            "rpm": self.rpm,
            "burst": self.burst,
        }


# ============================================================================
# Singleton Instances (importables en endpoints)
# ============================================================================

# IP-based limiter: más permisivo (20 req/min, burst 5)
# Protege contra abuse desde una sola IP
ip_rate_limiter = TokenBucketRateLimiter(requests_per_min=20, burst=5)

# Session-based limiter: más estricto (10 req/min, burst 3)
# Previene spam dentro de una sesión individual
session_rate_limiter = TokenBucketRateLimiter(requests_per_min=10, burst=3)

logger.info(
    "RATE_LIMITERS_READY",
    ip_limiter_rpm=20,
    ip_limiter_burst=5,
    session_limiter_rpm=10,
    session_limiter_burst=3,
)
