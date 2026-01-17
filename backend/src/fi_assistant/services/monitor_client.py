"""FI Monitor Client - GPU Embedding with Circuit Breaker.

Provides GPU-accelerated embeddings via FI Monitor with automatic fallback to CPU.

Architecture:
  1. Try Monitor GPU cache first (fast: 20-50ms)
  2. Fallback to local CPU if unavailable (slower: 100-150ms)
  3. Circuit breaker prevents cascade failures

Circuit Breaker Logic:
  - 3 consecutive failures → open circuit for 60 seconds
  - During open circuit: skip Monitor, use CPU directly
  - After 60s: half-open (try Monitor once)
  - If success: close circuit (back to normal)

Author: Bernard Uriza Orozco
Created: 2026-01-16
Card: Phase 2 - Fallback & Resilience
"""

from __future__ import annotations

import time
from typing import Optional

import httpx
import numpy as np
from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Circuit Breaker
# ============================================================================


class CircuitBreaker:
    """Circuit breaker for Monitor GPU service.

    Prevents cascade failures by opening circuit after repeated failures.
    """

    def __init__(self, failure_threshold: int = 3, timeout_seconds: int = 60):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying again (half-open)
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.opened_at: Optional[float] = None

    def is_open(self) -> bool:
        """Check if circuit is open.

        Returns:
            True if circuit is open (should NOT call Monitor)
        """
        if self.opened_at is None:
            return False

        # Check if timeout elapsed (half-open)
        elapsed = time.time() - self.opened_at
        if elapsed > self.timeout_seconds:
            logger.info(
                "CIRCUIT_BREAKER_HALF_OPEN",
                elapsed_seconds=int(elapsed),
                timeout_seconds=self.timeout_seconds,
            )
            self.reset()
            return False

        return True

    def on_success(self):
        """Record successful Monitor call."""
        if self.failures > 0 or self.opened_at is not None:
            logger.info(
                "CIRCUIT_BREAKER_SUCCESS",
                previous_failures=self.failures,
                was_open=self.opened_at is not None,
            )
        self.failures = 0
        self.opened_at = None

    def on_failure(self):
        """Record failed Monitor call."""
        self.failures += 1

        if self.failures >= self.failure_threshold and self.opened_at is None:
            self.opened_at = time.time()
            logger.warning(
                "CIRCUIT_BREAKER_OPENED",
                failures=self.failures,
                timeout_seconds=self.timeout_seconds,
            )

    def reset(self):
        """Reset circuit breaker (for testing or manual intervention)."""
        self.failures = 0
        self.opened_at = None
        logger.info("CIRCUIT_BREAKER_RESET")


# Global circuit breaker for Monitor
_monitor_circuit_breaker = CircuitBreaker()


def reset_monitor_circuit_breaker():
    """Reset circuit breaker (for testing or manual recovery)."""
    _monitor_circuit_breaker.reset()


# ============================================================================
# Monitor Discovery
# ============================================================================


async def discover_monitor_url() -> Optional[str]:
    """Discover FI Monitor URL from Azure Blob Storage.

    FI Monitor uploads its tunnel URL to Azure Blob on startup.

    Returns:
        Monitor tunnel URL or None if unavailable
    """
    # TODO: Implement Azure Blob discovery
    # For now, check environment variable
    import os

    tunnel_url = os.getenv("OLLAMA_TUNNEL_URL")
    if tunnel_url:
        return tunnel_url

    # Try local file (for development)
    try:
        from pathlib import Path

        local_file = Path.home() / ".config" / "fi-monitor" / "tunnel-url.json"
        if local_file.exists():
            import json

            data = json.loads(local_file.read_text())
            return data.get("tunnel_url")
    except Exception:
        pass

    return None


# ============================================================================
# Embedding Functions
# ============================================================================


async def get_embedding_from_monitor(text: str, timeout: float = 0.2) -> np.ndarray:
    """Get embedding from Monitor GPU cache.

    Args:
        text: Text to embed
        timeout: Request timeout in seconds (default: 200ms)

    Returns:
        Embedding vector (384-dim)

    Raises:
        ConnectionError: If circuit is open or Monitor unavailable
        TimeoutError: If request exceeds timeout
    """
    if _monitor_circuit_breaker.is_open():
        raise ConnectionError("Circuit breaker open - skipping Monitor")

    # Discover Monitor URL
    monitor_url = await discover_monitor_url()
    if not monitor_url:
        _monitor_circuit_breaker.on_failure()
        raise ConnectionError("No Monitor URL available")

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{monitor_url}/rag/embed",
                json={"texts": [text]},
                headers={"X-API-Key": "change-me-in-production"},  # TODO: From env
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data["embeddings"]

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "MONITOR_EMBEDDING_SUCCESS",
            latency_ms=elapsed_ms,
            device=data.get("device", "unknown"),
        )

        _monitor_circuit_breaker.on_success()
        return np.array(embeddings[0])

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.warning(
            "MONITOR_EMBEDDING_FAILED",
            error=str(e),
            latency_ms=elapsed_ms,
        )
        _monitor_circuit_breaker.on_failure()
        raise


# Global model instance (lazy loaded)
_local_embedding_model = None


async def get_embedding_local_cpu(text: str) -> np.ndarray:
    """Get embedding using local CPU (fallback).

    This is the reliable fallback when Monitor GPU is unavailable.

    Args:
        text: Text to embed

    Returns:
        Embedding vector (384-dim)
    """
    global _local_embedding_model

    # Lazy load model (cached after first use)
    if _local_embedding_model is None:
        from sentence_transformers import SentenceTransformer

        start_time = time.time()
        _local_embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        load_time_ms = int((time.time() - start_time) * 1000)
        logger.info("LOCAL_EMBEDDING_MODEL_LOADED", load_time_ms=load_time_ms)

    start_time = time.time()
    embedding = _local_embedding_model.encode(
        [text],
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]
    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info("LOCAL_EMBEDDING_SUCCESS", latency_ms=elapsed_ms, device="cpu")
    return embedding


async def get_embedding_with_fallback(text: str) -> np.ndarray:
    """Get embedding with Monitor GPU + CPU fallback.

    This is the main entry point for embedding generation.

    Strategy:
      1. Try Monitor GPU (fast: 20-50ms)
      2. If unavailable, use local CPU (slower: 100-150ms)

    Args:
        text: Text to embed

    Returns:
        Embedding vector (384-dim) - always succeeds
    """
    try:
        return await get_embedding_from_monitor(text, timeout=0.2)
    except (ConnectionError, TimeoutError, Exception) as e:
        logger.info(
            "MONITOR_UNAVAILABLE_FALLBACK_CPU",
            error=str(e),
        )
        return await get_embedding_local_cpu(text)
