from __future__ import annotations

"""
Free Intelligence - LLM Cache

Disk-based cache for LLM responses with TTL and SHA-256 hashing.

File: backend/llm_cache.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001

Features:
- SHA-256 hash keys (provider|model|prompt|system|params)
- TTL: 30 minutes default
- Disk storage: /data/llm_cache/
- JSON serialization
"""

from backend.logger import get_logger

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict

logger = get_logger(__name__)


class LLMCache:
    """
    Disk-based cache for LLM responses.

    Key format: sha256(provider|model|prompt|system|params)
    Storage: /data/llm_cache/{hash}.json
    TTL: 30 minutes (configurable)
    """

    def __init__(self, cache_dir: str = "data/llm_cache", ttl_minutes: int = 30):
        """
        Initialize LLM cache.

        Args:
            cache_dir: Directory for cache files (relative to project root)
            ttl_minutes: Time-to-live in minutes
        """
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_minutes * 60

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "LLM_CACHE_INIT",
            cache_dir=str(self.cache_dir),
            ttl_minutes=ttl_minutes,
        )

    def _compute_key(
        self,
        provider: str,
        model: str,
        prompt: str,
        system: str = "",
        params: dict[str, Any | None] | None = None,
    ) -> str:
        """
        Compute SHA-256 hash key for cache entry.

        Args:
            provider: Provider name (ollama, claude)
            model: Model identifier
            prompt: User prompt
            system: System prompt (optional)
            params: Request parameters (temperature, max_tokens, etc.)

        Returns:
            SHA-256 hash string (64 chars)
        """
        params_str = json.dumps(params or {}, sort_keys=True)
        key_content = f"{provider}|{model}|{prompt}|{system}|{params_str}"
        return hashlib.sha256(key_content.encode()).hexdigest()

    def get(
        self,
        provider: str,
        model: str,
        prompt: str,
        system: str = "",
        params: dict[str, Any | None] | None = None,
    ) -> dict[str, Any | None] | None:
        """
        Get cached response if available and not expired.

        Args:
            provider: Provider name
            model: Model identifier
            prompt: User prompt
            system: System prompt
            params: Request parameters

        Returns:
            Cached response dict or None if not found/expired
        """
        cache_key = self._compute_key(provider, model, prompt, system, params)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            logger.debug("LLM_CACHE_MISS", cache_key=cache_key[:16], reason="not_found")
            return None

        try:
            with open(cache_file) as f:
                entry = json.load(f)

            # Check TTL
            cached_at = entry.get("cached_at", 0)
            age_seconds = time.time() - cached_at

            if age_seconds > self.ttl_seconds:
                logger.debug(
                    "LLM_CACHE_MISS",
                    cache_key=cache_key[:16],
                    reason="expired",
                    age_seconds=int(age_seconds),
                    ttl_seconds=self.ttl_seconds,
                )
                # Delete expired entry
                cache_file.unlink()
                return None

            logger.info(
                "LLM_CACHE_HIT",
                cache_key=cache_key[:16],
                age_seconds=int(age_seconds),
            )

            return entry.get("response")

        except Exception as e:
            logger.warning(
                "LLM_CACHE_READ_ERROR",
                cache_key=cache_key[:16],
                error=str(e),
            )
            return None

    def set(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: Dict[str, Any],
        system: str = "",
        params: dict[str, Any | None] | None = None,
    ) -> str:
        """
        Store response in cache.

        Args:
            provider: Provider name
            model: Model identifier
            prompt: User prompt
            response: LLM response dict to cache
            system: System prompt
            params: Request parameters

        Returns:
            Cache key (SHA-256 hash)
        """
        cache_key = self._compute_key(provider, model, prompt, system, params)
        cache_file = self.cache_dir / f"{cache_key}.json"

        try:
            entry = {
                "cached_at": time.time(),
                "provider": provider,
                "model": model,
                "prompt_hash": cache_key,
                "response": response,
            }

            with open(cache_file, "w") as f:
                json.dump(entry, f, indent=2)

            logger.info(
                "LLM_CACHE_SET",
                cache_key=cache_key[:16],
                cache_file=cache_file.name,
            )

            return cache_key

        except Exception as e:
            logger.error(
                "LLM_CACHE_WRITE_ERROR",
                cache_key=cache_key[:16],
                error=str(e),
            )
            raise

    def clear_expired(self) -> int:
        """
        Clear all expired cache entries.

        Returns:
            Number of entries cleared
        """
        cleared = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file) as f:
                    entry = json.load(f)

                cached_at = entry.get("cached_at", 0)
                age_seconds = now - cached_at

                if age_seconds > self.ttl_seconds:
                    cache_file.unlink()
                    cleared += 1

            except Exception as e:
                logger.warning(
                    "LLM_CACHE_CLEAR_ERROR",
                    cache_file=cache_file.name,
                    error=str(e),
                )

        if cleared > 0:
            logger.info("LLM_CACHE_CLEARED", entries_cleared=cleared)

        return cleared

    def clear_all(self) -> int:
        """
        Clear all cache entries (regardless of TTL).

        Returns:
            Number of entries cleared
        """
        cleared = 0

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                cleared += 1
            except Exception as e:
                logger.warning(
                    "LLM_CACHE_CLEAR_ERROR",
                    cache_file=cache_file.name,
                    error=str(e),
                )

        logger.info("LLM_CACHE_CLEARED_ALL", entries_cleared=cleared)
        return cleared

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (total entries, total size, oldest entry age)
        """
        entries = list(self.cache_dir.glob("*.json"))
        total_entries = len(entries)
        total_size = sum(f.stat().st_size for f in entries)
        oldest_age = 0

        if entries:
            now = time.time()
            for cache_file in entries:
                try:
                    with open(cache_file) as f:
                        entry = json.load(f)
                    cached_at = entry.get("cached_at", now)
                    age = now - cached_at
                    oldest_age = max(oldest_age, age)
                except:
                    pass

        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "oldest_age_seconds": int(oldest_age),
            "cache_dir": str(self.cache_dir),
        }


# Global cache instance (singleton)
_cache_instance: LLMCache | None = None


def get_cache(ttl_minutes: int = 30) -> LLMCache:
    """
    Get global LLM cache instance (singleton).

    Args:
        ttl_minutes: TTL in minutes (only used on first call)

    Returns:
        LLMCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache(ttl_minutes=ttl_minutes)
    return _cache_instance
