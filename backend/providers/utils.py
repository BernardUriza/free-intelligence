"""
Free Intelligence - LLM Provider Utilities

Utility functions shared across LLM providers:
- Embedding dimension normalization
- Error message sanitization (API key redaction)
"""

from __future__ import annotations

import re

import numpy as np

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


def pad_embedding_to_768(embedding: np.ndarray) -> np.ndarray:
    """
    Pad embedding vector to 768 dimensions if needed.

    Args:
        embedding: Input embedding vector (any dimension)

    Returns:
        768-dimensional embedding (zero-padded if needed)

    Examples:
        >>> emb_384 = np.random.rand(384).astype(np.float32)
        >>> emb_768 = pad_embedding_to_768(emb_384)
        >>> assert emb_768.shape == (768,)
        >>> assert np.array_equal(emb_768[:384], emb_384)
    """
    if embedding.shape[0] == 768:
        return embedding

    if embedding.shape[0] > 768:
        logger.warning(
            "EMBEDDING_TRUNCATED",
            from_dim=embedding.shape[0],
            to_dim=768,
            message="Embedding larger than 768, truncating",
        )
        return embedding[:768]

    # Pad to 768 dimensions
    padded = np.zeros(768, dtype=np.float32)
    padded[: embedding.shape[0]] = embedding

    logger.info("EMBEDDING_PADDED", from_dim=embedding.shape[0], to_dim=768)

    return padded


def sanitize_error_message(error_msg: str, max_length: int = 100) -> str:
    """
    Sanitize error messages to remove API keys and sensitive data.

    Args:
        error_msg: Raw error message
        max_length: Maximum length of output (default: 100). Use 0 for no limit.

    Returns:
        Sanitized and truncated error message

    Examples:
        >>> sanitize_error_message("API key sk-ant-api03-abc123 is invalid")
        'API key [REDACTED] is invalid'
    """
    # Pattern for Anthropic API keys: sk-ant-api03-XXXX
    error_msg = re.sub(r"sk-ant-api\d+-[A-Za-z0-9_-]+", "[REDACTED_API_KEY]", error_msg)

    # Pattern for generic API keys
    error_msg = re.sub(
        r'api[_-]?key["\']?\s*[:=]\s*["\']?[A-Za-z0-9_-]{20,}',
        "api_key=[REDACTED]",
        error_msg,
        flags=re.IGNORECASE,
    )

    # Pattern for bearer tokens
    error_msg = re.sub(
        r"Bearer\s+[A-Za-z0-9_-]{20,}", "Bearer [REDACTED_TOKEN]", error_msg, flags=re.IGNORECASE
    )

    # Truncate if max_length specified
    if max_length > 0 and len(error_msg) > max_length:
        return error_msg[:max_length] + "..."

    return error_msg
