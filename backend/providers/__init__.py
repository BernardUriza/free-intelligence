"""
Backend LLM Providers - Unified interface for multi-provider LLM access.

Free Intelligence provides a provider-agnostic abstraction layer for LLM
interactions, supporting:
- Claude (Anthropic) - Primary for production
- Ollama (Local inference) - Offline-first operation
- Azure OpenAI (GPT-4, GPT-4o) - Enterprise cloud option

Philosophy: Provider-agnostic design. No vendor lock-in.
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
from backend.providers.claude import ClaudeProvider
from backend.providers.ollama import OllamaProvider
from backend.providers.azure_openai import AzureOpenAIProvider

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
    "ClaudeProvider",
    "OllamaProvider",
    "AzureOpenAIProvider",
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
