"""
Free Intelligence - Shared Embedding Utilities

Provides fallback embedding generation for providers without native support.
Used by ClaudeProvider and AzureOpenAIProvider.
"""

from __future__ import annotations

import numpy as np

from backend.utils.common.logging.logger import get_logger

# Optional: sentence_transformers (requires torch, not installed in production)
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore

logger = get_logger(__name__)


def fallback_embed_sentence_transformer(
    text: str,
    model_name: str = "all-MiniLM-L6-v2",
    provider_name: str = "unknown",
) -> np.ndarray:
    """
    Generate embedding using sentence-transformers as fallback.

    Used by providers without native embedding support (Claude, Azure OpenAI).

    Args:
        text: Input text to embed
        model_name: SentenceTransformer model to use (default: all-MiniLM-L6-v2)
        provider_name: Name of the calling provider (for logging)

    Returns:
        numpy array with embedding vector

    Raises:
        RuntimeError: If sentence_transformers is not available (requires torch)

    Note:
        sentence_transformers requires torch which is heavy (~2GB).
        Not available in production mode to keep deployments lean.
    """
    logger.warning(
        "EMBED_FALLBACK_SENTENCE_TRANSFORMER",
        provider=provider_name,
        model=model_name,
        message=f"{provider_name} doesn't support embeddings, falling back to sentence-transformers",
    )

    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence_transformers not available (requires torch). "
            "Embeddings are disabled in production mode."
        )

    # Use lightweight model
    model = SentenceTransformer(model_name)
    embedding: np.ndarray = model.encode(text, convert_to_numpy=True)

    logger.info(
        "EMBED_FALLBACK_COMPLETED",
        provider=provider_name,
        embedding_dim=len(embedding),
        model=model_name,
    )

    return embedding
