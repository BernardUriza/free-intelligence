from __future__ import annotations

"""
Free Intelligence - LLM Adapter

Unified interface for LLM providers (Claude, Ollama).

File: backend/llm_adapter.py
Created: 2025-10-28
Card: FI-CORE-FEAT-007

Architecture:
- Abstract base class LLMAdapter
- Provider implementations: ClaudeAdapter, OllamaAdapter (stub)
- Unified methods: generate(), stream(), summarize()
- Features: timeouts, budget tracking, retries, local logging
- No PHI in logs (redaction)
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from backend.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class LLMRequest:
    """LLM request parameters"""

    prompt: str
    schema: Optional[dict[str, Any]] = None  # JSON Schema for structured output
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: Optional[str] = None
    timeout_seconds: int = 30
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """LLM response with metadata"""

    content: str
    provider: str
    model: str
    tokens_used: int
    latency_ms: int
    finish_reason: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat() + "Z")


@dataclass
class LLMBudget:
    """Budget tracking for LLM usage"""

    max_tokens_per_hour: int = 100_000
    max_requests_per_hour: int = 100
    tokens_used: int = 0
    requests_made: int = 0
    period_start: float = field(default_factory=time.time)

    def reset_if_needed(self):
        """Reset counters if hour has passed"""
        now = time.time()
        if now - self.period_start >= 3600:  # 1 hour
            self.tokens_used = 0
            self.requests_made = 0
            self.period_start = now

    def can_make_request(self, estimated_tokens: int = 4096) -> bool:
        """Check if request is within budget"""
        self.reset_if_needed()
        return (
            self.requests_made < self.max_requests_per_hour
            and self.tokens_used + estimated_tokens <= self.max_tokens_per_hour
        )

    def track_request(self, tokens: int):
        """Track a completed request"""
        self.requests_made += 1
        self.tokens_used += tokens


# ============================================================================
# BASE ADAPTER
# ============================================================================


class LLMAdapter(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement:
    - generate(): Single response
    - stream(): Streaming response
    - summarize(): Text summarization
    """

    def __init__(
        self,
        provider_name: str,
        model: str,
        budget: Optional[LLMBudget] = None,
        max_retries: int = 3,
    ):
        self.provider_name = provider_name
        self.model = model
        self.budget = budget or LLMBudget()
        self.max_retries = max_retries

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a single response.

        Args:
            request: LLM request with prompt and parameters

        Returns:
            LLM response with content and metadata

        Raises:
            BudgetExceededError: If budget is exceeded
            TimeoutError: If request times out
            LLMProviderError: If provider fails
        """
        pass

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[str]:
        """
        Stream response chunks.

        Args:
            request: LLM request with prompt and parameters

        Yields:
            Response chunks as they arrive

        Raises:
            BudgetExceededError: If budget is exceeded
            TimeoutError: If request times out
            LLMProviderError: If provider fails
        """
        pass

    def summarize(self, text: str, max_length: int = 200) -> LLMResponse:
        """
        Summarize text (convenience method).

        Args:
            text: Text to summarize
            max_length: Maximum summary length in words

        Returns:
            LLM response with summary
        """
        prompt = f"Summarize the following text in {max_length} words or less:\n\n{text}"
        request = LLMRequest(
            prompt=prompt,
            max_tokens=max_length * 2,  # ~2 tokens per word
            temperature=0.5,
        )
        return self.generate(request)

    def redact_phi(self, text: str) -> str:
        """
        Redact PHI from text for logging.

        Simple redaction: replace common patterns with [REDACTED]
        """
        import re

        # Email addresses
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)

        # Phone numbers (US format)
        text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", text)

        # SSN-like patterns
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)

        return text


# ============================================================================
# EXCEPTIONS
# ============================================================================


class LLMError(Exception):
    """Base exception for LLM errors"""

    pass


class BudgetExceededError(LLMError):
    """Budget exceeded"""

    pass


class LLMProviderError(LLMError):
    """Provider error"""

    pass


class NotImplementedProviderError(LLMError):
    """Provider not implemented (stub)"""

    pass


# ============================================================================
# FACTORY
# ============================================================================


def create_adapter(
    provider: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    budget: Optional[LLMBudget] = None,
) -> LLMAdapter:
    """
    Factory to create LLM adapters.

    Args:
        provider: Provider name ("claude" or "ollama")
        model: Model name (provider-specific, optional)
        api_key: API key for provider (if required)
        budget: Budget tracker (optional)

    Returns:
        LLMAdapter instance

    Raises:
        ValueError: If provider is unknown
        NotImplementedProviderError: If provider is stub
    """
    from backend.providers.claude import ClaudeAdapter
    from backend.providers.ollama import OllamaAdapter

    if provider.lower() == "claude":
        return ClaudeAdapter(
            model=model or "claude-3-5-sonnet-20241022",
            api_key=api_key,
            budget=budget,
        )
    elif provider.lower() == "ollama":
        return OllamaAdapter(
            model=model or "llama3.2",
            budget=budget,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
