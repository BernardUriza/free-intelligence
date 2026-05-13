"""LLM-provider-agnostic primitives.

This package intentionally does NOT wrap Anthropic and OpenAI under a
unified `LLMClient` — see `shared/__init__.py` for the rationale. What
DOES belong here is the cross-cutting timing math: retry backoff, jitter,
and rate-limit header parsing. These are pure functions over numbers
and dict-like headers; they are identical across providers.
"""

from shared.llm.retry import (
    BACKOFF_CAP_5XX,
    BACKOFF_CAP_429,
    BACKOFF_CAP_TIMEOUT,
    MAX_TIMEOUT_RETRIES,
    full_jitter_backoff,
    parse_retry_after,
)

__all__ = [
    "BACKOFF_CAP_5XX",
    "BACKOFF_CAP_429",
    "BACKOFF_CAP_TIMEOUT",
    "MAX_TIMEOUT_RETRIES",
    "full_jitter_backoff",
    "parse_retry_after",
]
