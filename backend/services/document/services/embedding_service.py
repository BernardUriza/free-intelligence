"""Embedding generation service for semantic search.

Delegates to FI Monitor GPU service for embeddings.
Uses Ollama + GPU acceleration via monitor_client.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Updated: 2026-01-29 (Refactored to use monitor_client)
Card: Document Repository Implementation
"""

from __future__ import annotations

import numpy as np

from backend.services.assistant.services.monitor_client import (
    get_embedding as get_embedding_from_monitor,
)
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text using FI Monitor GPU service.

    Args:
        text: Input text (sentence, paragraph, or document)

    Returns:
        Embedding vector (list of floats, dimension 384)

    Raises:
        ConnectionError: If FI Monitor unavailable
        ValueError: If text is empty
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")

    try:
        # Get embedding from FI Monitor GPU service
        embedding_array = await get_embedding_from_monitor(text)

        # Convert numpy array to list for JSON serialization
        return embedding_array.tolist()

    except Exception as e:
        logger.error(
            "EMBEDDING_GENERATION_ERROR",
            text_length=len(text),
            error=str(e),
            error_type=type(e).__name__
        )
        raise


async def generate_embeddings_batch(
    texts: list[str],
    batch_size: int = 32
) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Note: Currently processes sequentially. FI Monitor doesn't support batch API yet.
    TODO: Add batch endpoint to FI Monitor for better performance.

    Args:
        texts: List of input texts
        batch_size: Ignored (for API compatibility)

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    embeddings = []
    for text in texts:
        try:
            embedding = await generate_embedding(text)
            embeddings.append(embedding)
        except Exception as e:
            logger.warning(
                "BATCH_EMBEDDING_ITEM_FAILED",
                text_length=len(text),
                error=str(e)
            )
            # Add zero vector as fallback
            embeddings.append([0.0] * 384)  # 384-dim zero vector

    return embeddings


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1, higher is more similar)
    """
    a = np.array(vec1)
    b = np.array(vec2)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


__all__ = [
    "generate_embedding",
    "generate_embeddings_batch",
    "cosine_similarity",
]
