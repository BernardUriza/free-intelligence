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

import os
import time

import httpx
import numpy as np
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Monitor Discovery
# ============================================================================


async def discover_monitor_url() -> str | None:
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
        # Get API key from environment (default for dev)
        api_key = os.getenv("FI_MONITOR_API_KEY", "dev-key-local-only")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{monitor_url}/rag/embed",
                json={"texts": [text]},
                headers={"X-API-Key": api_key},
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


# ============================================================================
# Ollama Chat Functions
# ============================================================================


async def similarity_search_gpu(
    query_vector: list[float],
    document_vectors: list[list[float]],
    timeout: float = 30.0,
) -> list[float]:
    """Delegate similarity search to fi_monitor GPU service.

    10-200x faster than CPU for large batches (1000+ vectors).

    Args:
        query_vector: Query embedding (384 dims)
        document_vectors: List of document embeddings to search
        timeout: Request timeout in seconds (default: 30s)

    Returns:
        Similarity scores (0-1) for each document vector

    Raises:
        ConnectionError: If fi_monitor unavailable
        ValueError: If dimensions mismatch
    """
    # Discover Monitor URL
    monitor_url = await discover_monitor_url()
    if not monitor_url:
        raise ConnectionError("FI Monitor not available - tunnel URL not found")

    start_time = time.time()

    try:
        # Get API key from environment (default for dev)
        api_key = os.getenv("FI_MONITOR_API_KEY", "dev-key-local-only")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{monitor_url}/rag/similarity-search",
                json={
                    "query_vector": query_vector,
                    "document_vectors": document_vectors,
                },
                headers={"X-API-Key": api_key},
            )

            if response.status_code == 401:
                raise ConnectionError("Fi Monitor API key invalid")
            elif response.status_code == 400:
                raise ValueError(f"Invalid request: {response.json()['detail']}")
            elif response.status_code != 200:
                raise ConnectionError(f"Fi Monitor error: {response.status_code}")

            data = response.json()

            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "GPU_SIMILARITY_SEARCH",
                num_vectors=len(document_vectors),
                device=data["device_used"],
                duration_ms=data["duration_ms"],
                total_latency_ms=elapsed_ms,
            )

            return data["similarities"]

    except httpx.TimeoutException:
        raise ConnectionError("Fi Monitor timeout (>30s)")
    except httpx.ConnectError:
        raise ConnectionError("Fi Monitor unavailable - is it running?")


async def get_ollama_chat(
    messages: list[dict[str, str]],
    model: str = "llama3.1:8b",
    temperature: float = 0.7,
    timeout: float = 30.0,
) -> str:
    """Get chat completion from Ollama via Monitor.

    Args:
        messages: List of {"role": "system|user|assistant", "content": "..."}
        model: Ollama model name (default: llama3.1:8b)
        temperature: Sampling temperature 0-2 (default: 0.7)
        timeout: Request timeout in seconds (default: 30s)

    Returns:
        Assistant's response text

    Raises:
        ConnectionError: If Monitor/Ollama unavailable
        TimeoutError: If request exceeds timeout
    """
    # Discover Monitor URL
    monitor_url = await discover_monitor_url()
    if not monitor_url:
        raise ConnectionError("FI Monitor not available - tunnel URL not found")

    start_time = time.time()

    try:
        # Get API key from environment (default for dev)
        api_key = os.getenv("FI_MONITOR_API_KEY", "dev-key-local-only")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{monitor_url}/ollama/chat",
                json={
                    "messages": messages,
                    "model": model,
                    "temperature": temperature,
                },
                headers={"X-API-Key": api_key},
            )
            response.raise_for_status()
            data = response.json()
            assistant_message = data["message"]["content"]

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "MONITOR_OLLAMA_CHAT_SUCCESS",
            latency_ms=elapsed_ms,
            model=model,
            response_length=len(assistant_message),
        )

        return assistant_message

    except httpx.TimeoutException as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "MONITOR_OLLAMA_CHAT_TIMEOUT",
            error=str(e),
            latency_ms=elapsed_ms,
            timeout_s=timeout,
        )
        raise TimeoutError(f"Ollama chat timeout after {timeout}s: {e}") from e

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "MONITOR_OLLAMA_CHAT_FAILED",
            error=str(e),
            latency_ms=elapsed_ms,
        )
        raise ConnectionError(f"FI Monitor Ollama unavailable: {e}") from e
