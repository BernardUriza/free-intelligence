"""FastAPI Dependency Injection providers for Cache infrastructure.

Provides singleton ICache dependency for services.

Author: Claude Code
Created: 2026-02-02 (Phase 2.3 - DI Refactor - Circular Import Fix)
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.infrastructure.cache.interfaces.icache import ICache


@lru_cache(maxsize=1)
def _get_cache_singleton() -> "ICache":
    """Internal singleton factory for LLMCache with default TTL."""
    from backend.infrastructure.cache.cache import LLMCache

    return LLMCache(default_ttl=3600)


def get_cache_dep(ttl: int = 3600) -> "ICache":  # noqa: ARG001
    """Get LLM cache singleton for services.

    Args:
        ttl: Ignored. Singleton uses fixed TTL of 3600s (1 hour).

    Returns:
        ICache singleton instance (LLMCache)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    _ = ttl  # Ignored - singleton uses fixed TTL
    return _get_cache_singleton()


__all__ = ["get_cache_dep"]
