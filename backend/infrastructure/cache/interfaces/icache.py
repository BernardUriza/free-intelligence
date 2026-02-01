"""Interface for LLM Cache - enables dependency injection.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Mercurio (Cache consolidation)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ICache(ABC):
    """Abstract interface for LLM response caching.

    This interface defines the contract for caching LLM responses.
    Services depend on this interface, not the concrete LLMCache implementation.

    Key design decisions:
    - Hash-based keys (no PHI in cache keys)
    - TTL-based expiration
    - Hit rate tracking for observability
    """

    @abstractmethod
    def compute_key(
        self,
        prompt: str,
        temperature: float,
        model: str,
        schema: str | None = None,
    ) -> str:
        """Compute cache key from prompt + parameters.

        Args:
            prompt: Input prompt
            temperature: LLM temperature
            model: Model identifier
            schema: Optional JSON schema name

        Returns:
            SHA256 hash (64 hex chars)
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Get value from cache if exists and not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if miss/expired
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL (uses default if None)
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Stats dictionary with size, hits, misses, hit_rate, etc.
        """
        pass

    @abstractmethod
    def clear_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries evicted
        """
        pass

    @abstractmethod
    def clear_all(self) -> int:
        """Clear entire cache.

        Returns:
            Number of entries cleared
        """
        pass
