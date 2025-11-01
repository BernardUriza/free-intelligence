"""
Free Intelligence - Local Cache

Hash-based LLM response caching with TTL.

Philosophy:
- No PHI in cache keys (hash prompt + schema)
- Local in-memory cache (no Redis/external deps)
- Automatic expiration (TTL)
- Cache warming from preset examples

File: backend/cache.py
Created: 2025-10-28
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Optional

from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with TTL"""

    key: str
    value: Any
    created_at: float  # Unix timestamp
    ttl_seconds: int
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        age = time.time() - self.created_at
        return age > self.ttl_seconds

    def get_age_seconds(self) -> float:
        """Get age in seconds"""
        return time.time() - self.created_at


class LLMCache:
    """
    In-memory cache for LLM responses with hash-based keys.

    Features:
    - Hash(prompt + schema + temperature + model) → cache key
    - TTL-based expiration
    - No PHI in keys
    - Hit rate tracking
    - Prometheus export
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache.

        Args:
            default_ttl: Default TTL in seconds (1 hour)
        """
        self._cache: dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.total_hits = 0
        self.total_misses = 0
        self.total_evictions = 0
        logger.info("LLM_CACHE_INITIALIZED", default_ttl=default_ttl)

    def compute_key(
        self, prompt: str, temperature: float, model: str, schema: Optional[str] = None
    ) -> str:
        """
        Compute cache key from prompt + parameters.

        Args:
            prompt: Input prompt
            temperature: LLM temperature
            model: Model identifier
            schema: Optional JSON schema name

        Returns:
            SHA256 hash (64 hex chars)

        Examples:
            >>> cache = LLMCache()
            >>> key1 = cache.compute_key("test", 0.7, "claude-3-5-sonnet-20241022")
            >>> key2 = cache.compute_key("test", 0.7, "claude-3-5-sonnet-20241022")
            >>> assert key1 == key2
            >>> key3 = cache.compute_key("different", 0.7, "claude-3-5-sonnet-20241022")
            >>> assert key1 != key3
        """
        components = [prompt, str(temperature), model, schema or ""]
        combined = "|".join(components)
        key_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        logger.debug(
            "CACHE_KEY_COMPUTED",
            prompt_len=len(prompt),
            temperature=temperature,
            model=model,
            key=key_hash[:16],
        )  # Log prefix only

        return key_hash

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if miss/expired
        """
        entry = self._cache.get(key)

        if entry is None:
            self.total_misses += 1
            logger.debug("CACHE_MISS", key=key[:16])
            return None

        if entry.is_expired():
            # Expired - evict
            del self._cache[key]
            self.total_evictions += 1
            self.total_misses += 1
            logger.debug(
                "CACHE_EXPIRED", key=key[:16], age=entry.get_age_seconds(), ttl=entry.ttl_seconds
            )
            return None

        # Hit!
        entry.hits += 1
        self.total_hits += 1
        logger.debug("CACHE_HIT", key=key[:16], age=entry.get_age_seconds(), hits=entry.hits)

        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL (uses default if None)
        """
        ttl = ttl_seconds or self.default_ttl

        entry = CacheEntry(key=key, value=value, created_at=time.time(), ttl_seconds=ttl)

        self._cache[key] = entry

        logger.debug("CACHE_SET", key=key[:16], ttl=ttl, cache_size=len(self._cache))

    def clear_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries evicted
        """
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]

        self.total_evictions += len(expired_keys)

        if expired_keys:
            logger.info("CACHE_CLEANUP", evicted=len(expired_keys), remaining=len(self._cache))

        return len(expired_keys)

    def clear_all(self) -> int:
        """
        Clear entire cache.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info("CACHE_CLEARED", count=count)
        return count

    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as fraction (0.0 to 1.0)
        """
        total = self.total_hits + self.total_misses
        if total == 0:
            return 0.0
        return self.total_hits / total

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Stats dictionary for metrics export
        """
        return {
            "size": len(self._cache),
            "hits": self.total_hits,
            "misses": self.total_misses,
            "evictions": self.total_evictions,
            "hit_rate": self.get_hit_rate(),
            "oldest_age_seconds": self._get_oldest_age(),
        }

    def _get_oldest_age(self) -> Optional[float]:
        """Get age of oldest entry in seconds"""
        if not self._cache:
            return None

        oldest = min(entry.created_at for entry in self._cache.values())

        return time.time() - oldest

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus text format
        """
        stats = self.get_stats()

        lines = [
            "# HELP llm_cache_size Number of entries in cache",
            "# TYPE llm_cache_size gauge",
            f"llm_cache_size {stats['size']}",
            "",
            "# HELP llm_cache_hits_total Total cache hits",
            "# TYPE llm_cache_hits_total counter",
            f"llm_cache_hits_total {stats['hits']}",
            "",
            "# HELP llm_cache_misses_total Total cache misses",
            "# TYPE llm_cache_misses_total counter",
            f"llm_cache_misses_total {stats['misses']}",
            "",
            "# HELP llm_cache_evictions_total Total cache evictions",
            "# TYPE llm_cache_evictions_total counter",
            f"llm_cache_evictions_total {stats['evictions']}",
            "",
            "# HELP llm_cache_hit_rate Cache hit rate (0.0 to 1.0)",
            "# TYPE llm_cache_hit_rate gauge",
            f"llm_cache_hit_rate {stats['hit_rate']:.4f}",
            "",
        ]

        if stats["oldest_age_seconds"] is not None:
            lines.extend(
                [
                    "# HELP llm_cache_oldest_age_seconds Age of oldest entry",
                    "# TYPE llm_cache_oldest_age_seconds gauge",
                    f"llm_cache_oldest_age_seconds {stats['oldest_age_seconds']:.2f}",
                    "",
                ]
            )

        return "\n".join(lines)


# Global singleton cache instance
_cache_instance: Optional[LLMCache] = None


def get_cache(ttl: Optional[int] = None) -> LLMCache:
    """
    Get global cache instance (singleton).

    Args:
        ttl: Default TTL (only used on first call)

    Returns:
        Global LLMCache instance
    """
    global _cache_instance

    if _cache_instance is None:
        default_ttl = ttl or 3600
        _cache_instance = LLMCache(default_ttl=default_ttl)

    return _cache_instance


def clear_cache() -> int:
    """
    Clear global cache.

    Returns:
        Number of entries cleared
    """
    cache = get_cache()
    return cache.clear_all()


def get_cache_stats() -> dict[str, Any]:
    """
    Get global cache statistics.

    Returns:
        Stats dictionary
    """
    cache = get_cache()
    return cache.get_stats()


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        print("🔄 LLM Cache Demo\n")

        cache = get_cache(ttl=60)  # 60 second TTL

        # Test 1: Cache miss
        key1 = cache.compute_key("test prompt", 0.7, "claude-3-5-sonnet-20241022")
        result = cache.get(key1)
        print(f"Test 1 - Cache miss: {result is None}")

        # Test 2: Cache set
        cache.set(key1, {"response": "test output", "tokens": 100})
        print("Test 2 - Stored value")

        # Test 3: Cache hit
        result = cache.get(key1)
        print(f"Test 3 - Cache hit: {result is not None}")

        # Test 4: Different key
        key2 = cache.compute_key("different prompt", 0.7, "claude-3-5-sonnet-20241022")
        result = cache.get(key2)
        print(f"Test 4 - Different key miss: {result is None}")

        # Test 5: Stats
        stats = cache.get_stats()
        print("\n📊 Cache Stats:")
        print(f"  Size: {stats['size']}")
        print(f"  Hits: {stats['hits']}")
        print(f"  Misses: {stats['misses']}")
        print(f"  Hit Rate: {stats['hit_rate']:.1%}")

        # Test 6: Prometheus export
        print("\n📈 Prometheus Export:")
        print(cache.export_prometheus())

    else:
        print("Usage: python3 backend/cache.py demo")
