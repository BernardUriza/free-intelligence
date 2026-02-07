"""
Free Intelligence - LLM Generation Entry Points

Main entry points for LLM text generation and embeddings.
Provides high-level API with policy-based configuration.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

import numpy as np

from backend.providers.base import LLMResponse
from backend.providers.factory import get_provider
from backend.providers.response_parsers import QwenThinkingParser
from backend.providers.utils import sanitize_error_message
from backend.schemas.llm.audit_policy import require_audit_log
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


@require_audit_log
def llm_generate(
    prompt: str,
    provider: str | None = None,
    provider_config: dict[str, Any] | None = None,
    **kwargs: Any,
) -> LLMResponse:
    """
    Generate text completion using specified LLM provider.

    This is the main entry point for LLM text generation in Free Intelligence.
    Automatically logs to audit_logs.

    Args:
        prompt: Input text prompt
        provider: Provider name ("claude", "ollama", "azure"). If None, uses primary_provider from policy.
        provider_config: Provider-specific configuration (model, timeout, etc.). If None, uses policy config.
        **kwargs: Additional provider-specific parameters (override policy defaults)

    Returns:
        LLMResponse with content and metadata

    Example:
        >>> # Use policy defaults
        >>> response = llm_generate("What is Free Intelligence?")

        >>> # Override provider
        >>> response = llm_generate(
        ...     "What is Free Intelligence?",
        ...     provider="claude",
        ...     temperature=0.7,
        ...     max_tokens=1024
        ... )
    """
    # Load policy singleton (Phase 2.3 DI Refactor - uses @lru_cache singleton)
    from backend.services.workflow.dependencies import get_policy_loader_dep

    policy_loader = get_policy_loader_dep()  # Singleton - no repeated YAML parsing

    # Use primary provider from policy if not specified
    if provider is None:
        provider = policy_loader.get_primary_provider()
        logger.info("LLM_PROVIDER_FROM_POLICY", provider=provider)

    # Load provider config from policy if not specified
    if provider_config is None:
        provider_config = policy_loader.get_provider_config(provider)

    # Ensure provider_config is not None
    if provider_config is None:
        provider_config = {}

    logger.info("LLM_CONFIG_FROM_POLICY", provider=provider, model=provider_config.get("model"))

    logger.info(
        "LLM_GENERATE_STARTED",
        provider=provider,
        prompt_length=len(prompt),
        kwargs_keys=list(kwargs.keys()),
    )

    try:
        # Ensure provider is a string
        if not isinstance(provider, str):
            raise ValueError(f"Provider must be a string, got {type(provider)}")

        # Get provider instance
        logger.info("LLM_GETTING_PROVIDER", provider=provider)
        llm_provider = get_provider(provider, provider_config)
        logger.info("LLM_PROVIDER_CREATED", provider_type=type(llm_provider).__name__)

        # Generate response
        logger.info(
            "LLM_CALLING_GENERATE",
            provider=provider,
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature"),
        )

        response = llm_provider.generate(prompt, **kwargs)

        logger.info("LLM_GENERATE_RETURNED")

        logger.info(
            "LLM_GENERATE_COMPLETED",
            provider=provider,
            model=response.model,
            tokens=response.tokens_used,
            latency_ms=response.latency_ms,
        )

        return response

    except Exception as e:
        sanitized_error = sanitize_error_message(str(e))
        logger.error(
            "LLM_GENERATE_FAILED",
            provider=provider,
            error=sanitized_error,
            error_type=type(e).__name__,
        )
        raise


@lru_cache(maxsize=10000)
def _cached_embed(text_hash: str, text: str, provider: str) -> bytes:
    """
    Internal cached embedding function.

    Args:
        text_hash: SHA256 hash of text (for cache key)
        text: Input text to embed
        provider: Provider name

    Returns:
        Embedding vector as bytes

    Note: Uses text_hash as cache key to avoid memory issues with large texts.
    """
    logger.info("EMBEDDING_CACHE_MISS", text_hash=text_hash[:16], provider=provider)

    llm_provider = get_provider(provider, None)
    embedding = llm_provider.embed(text)

    # Convert to bytes for caching
    return embedding.tobytes()


def llm_embed(text: str, provider: str = "claude") -> np.ndarray:
    """
    Generate embedding vector for text with LRU caching.

    Note: Claude doesn't support embeddings, falls back to sentence-transformers.
    Ollama (future) will support embeddings natively.

    Caching: Uses LRU cache (10,000 entries) to avoid re-embedding same text.
    Cache key is SHA256 hash of text to handle large inputs efficiently.

    Args:
        text: Input text to embed
        provider: Provider name

    Returns:
        numpy array with embedding vector (typically 384 or 768 dimensions)

    Examples:
        >>> # First call - cache miss
        >>> emb1 = llm_embed("What is Free Intelligence?")
        >>> # Second call - cache hit (instant)
        >>> emb2 = llm_embed("What is Free Intelligence?")
        >>> assert np.array_equal(emb1, emb2)
    """
    # Compute hash for cache key
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    logger.info(
        "LLM_EMBED_STARTED", provider=provider, text_length=len(text), text_hash=text_hash[:16]
    )

    try:
        # Get cache info before call (to detect hit vs miss)
        cache_info_before = _cached_embed.cache_info()

        # Try cached version
        embedding_bytes = _cached_embed(text_hash, text, provider)

        # Convert bytes back to numpy array
        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)

        # Get cache stats after call
        cache_info = _cached_embed.cache_info()

        # Detect if this was a cache hit or miss
        _was_cache_hit = cache_info.hits > cache_info_before.hits

        logger.info(
            "LLM_EMBED_COMPLETED",
            provider=provider,
            embedding_dim=len(embedding),
            cache_hits=cache_info.hits,
            cache_misses=cache_info.misses,
            cache_hit_rate=f"{cache_info.hits / (cache_info.hits + cache_info.misses) * 100:.1f}%"
            if (cache_info.hits + cache_info.misses) > 0
            else "0%",
        )

        return embedding

    except Exception as e:
        sanitized_error = sanitize_error_message(str(e))
        logger.error("LLM_EMBED_FAILED", provider=provider, error=sanitized_error)
        raise


def parse_qwen_thinking_and_response(text: str) -> tuple[str | None, str]:
    """Parse Qwen3 response text to separate thinking from content.

    Qwen3 models output their reasoning in XML-like tags:
        <think>reasoning here</think>actual response here

    This function extracts the thinking blocks and content separately.

    Args:
        text: Full response text from Qwen3 model

    Returns:
        (thinking, content) tuple where:
        - thinking: str | None - Concatenated reasoning (None if no thinking blocks)
        - content: str - Response content with thinking blocks removed

    Examples:
        >>> thinking, content = parse_qwen_thinking_and_response(
        ...     "<think>Let me analyze this</think>The answer is 42"
        ... )
        >>> thinking
        'Let me analyze this'
        >>> content
        'The answer is 42'

        >>> thinking, content = parse_qwen_thinking_and_response("Just a plain response")
        >>> thinking is None
        True
        >>> content
        'Just a plain response'
    """
    return QwenThinkingParser.parse_thinking_blocks(text)
