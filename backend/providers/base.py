"""
Free Intelligence - LLM Provider Base Types

Core types and abstract base class for LLM providers.
Part of the multi-provider abstraction layer.

Philosophy: Provider-agnostic design. No vendor lock-in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np

from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.utils.common.logging.logger import ILogger


class LLMProviderType(Enum):
    """Supported LLM providers"""

    CLAUDE = "claude"
    OLLAMA = "ollama"
    OPENAI = "openai"
    AZURE = "azure"


class LLMResponse:
    """Unified response format from any LLM provider"""

    __slots__ = (
        "content",
        "cost_usd",
        "latency_ms",
        "metadata",
        "model",
        "provider",
        "tokens_used",
    )

    content: str
    model: str
    provider: str
    tokens_used: int
    cost_usd: float | None
    latency_ms: float | None
    metadata: dict[str, Any] | None

    def __init__(
        self,
        content: str,
        model: str,
        provider: str,
        tokens_used: int,
        cost_usd: float | None = None,
        latency_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.content = content
        self.model = model
        self.provider = provider
        self.tokens_used = tokens_used
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        self.metadata = metadata


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    logger: "ILogger"
    config: dict[str, Any]

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """
        Generate text completion from prompt.

        Args:
            prompt: Input text prompt
            **kwargs: Provider-specific parameters (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with content and metadata
        """

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            numpy array with embedding vector
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name (claude, ollama, openai)"""
