"""FI Monitor Client - GPU Embedding Service.

Provides GPU-accelerated embeddings via FI Monitor.

Architecture:
  - FI Monitor runs Ollama (LLM) + RAG Service (GPU embeddings)
  - Both services must be available for chat to work
  - No fallback needed: if Monitor offline, chat offline

Author: Bernard Uriza Orozco
Created: 2026-01-16
Card: Phase 3 - Monitor GPU Cache
"""

from __future__ import annotations

import time
from typing import Optional

import httpx
import numpy as np
from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


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


async def get_embedding_from_monitor(text: str, timeout: float = 5.0) -> np.ndarray:
    """Get embedding from Monitor GPU service.

    Args:
        text: Text to embed
        timeout: Request timeout in seconds (default: 5s)

    Returns:
        Embedding vector (384-dim)

    Raises:
        ConnectionError: If Monitor unavailable
        TimeoutError: If request exceeds timeout
    """
    # Discover Monitor URL
    monitor_url = await discover_monitor_url()
    if not monitor_url:
        raise ConnectionError("FI Monitor not available - tunnel URL not found")

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

        return np.array(embeddings[0])

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "MONITOR_EMBEDDING_FAILED",
            error=str(e),
            latency_ms=elapsed_ms,
        )
        raise ConnectionError(f"FI Monitor GPU service unavailable: {e}") from e


async def get_embedding(text: str) -> np.ndarray:
    """Get embedding from Monitor GPU service.

    Main entry point for RAG embedding generation.

    Args:
        text: Text to embed

    Returns:
        Embedding vector (384-dim)

    Raises:
        ConnectionError: If FI Monitor unavailable
    """
    return await get_embedding_from_monitor(text)
