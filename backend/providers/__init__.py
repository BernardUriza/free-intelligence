"""
Backend LLM Providers - Unified interface for LLM access.

Free Intelligence cloud backend routes all LLM requests to FI Local
via Cloudflare Tunnel. This ensures PHI never leaves the clinic's
local infrastructure.

Supported:
- Ollama (routed to FI Local GPU via tunnel)

Note:
    Direct API providers (Claude, Azure) removed for PHI compliance.
    Embeddings handled by FI Local RAG service.
"""

from __future__ import annotations

# Core types
from backend.providers.base import (
    LLMProvider,
    LLMProviderType,
    LLMResponse,
)

# Utility functions
from backend.providers.utils import (
    pad_embedding_to_768,
    sanitize_error_message,
)

# Provider implementations
from backend.providers.ollama import OllamaProvider

# Factory
from backend.providers.factory import get_provider

# Entry points
from backend.providers.generate import (
    llm_generate,
    llm_embed,
    parse_qwen_thinking_and_response,
)

# Resilience patterns
from backend.providers.resilience import ResilienceExecutor

# Response parsing
from backend.providers.response_parsers import (
    QwenThinkingParser,
    GenericParser,
)

# Retry/Circuit breaker (re-export for convenience)
from backend.providers.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    RetryConfig,
    calculate_backoff_delay,
    get_circuit_breaker,
)

__all__ = [
    # Types
    "LLMProvider",
    "LLMProviderType",
    "LLMResponse",
    # Utilities
    "pad_embedding_to_768",
    "sanitize_error_message",
    # Providers
    "OllamaProvider",
    # Factory & entry points
    "get_provider",
    "llm_generate",
    "llm_embed",
    "parse_qwen_thinking_and_response",
    # Resilience
    "ResilienceExecutor",
    # Parsers
    "QwenThinkingParser",
    "GenericParser",
    # Retry/Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "RetryConfig",
    "calculate_backoff_delay",
    "get_circuit_breaker",
]
