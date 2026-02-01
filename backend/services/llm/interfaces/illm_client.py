"""LLM client interface.

Decouples services from specific LLM providers (OpenAI, Anthropic, Ollama).
Enables provider switching, A/B testing, and fallback strategies.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List


class ILLMClient(ABC):
    """LLM provider abstraction.

    Responsibilities:
    - Generate text completions
    - Generate structured outputs (JSON schema validation)
    - Stream responses for real-time UX
    - Handle provider-specific quirks (rate limits, retries, errors)

    Providers:
    - OpenAI (GPT-4, GPT-4o)
    - Anthropic (Claude 3.5 Sonnet, Claude 4 Opus)
    - Ollama (llama3, qwen2.5, local models)

    Clean Architecture Benefits:
    - Services don't know which provider they're using
    - Easy to mock for testing
    - Can swap providers without changing services
    - Load balancing and fallback strategies at infrastructure layer
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stop: List[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text completion.

        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            model: Model identifier (gpt-4, claude-3-5-sonnet, llama3)
            temperature: Sampling temperature 0.0-2.0 (0=deterministic)
            max_tokens: Maximum tokens to generate (None=provider default)
            stop: Stop sequences for generation
            **kwargs: Provider-specific parameters

        Returns:
            Generated text

        Raises:
            ValueError: If messages are empty or model is invalid
            IOError: If API call fails (network, auth, rate limit)
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        model: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output matching JSON schema.

        Args:
            messages: Chat messages
            schema: JSON schema for output validation
            model: Model identifier
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            Dict matching the provided schema

        Raises:
            ValueError: If schema is invalid or output doesn't match
            IOError: If API call fails
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream text completion token-by-token.

        Args:
            messages: Chat messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Yields:
            Text chunks as they're generated

        Raises:
            ValueError: If messages are empty or model is invalid
            IOError: If API call fails
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider identifier.

        Returns:
            Provider name (openai, anthropic, ollama)
        """
        pass

    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get list of supported models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    @abstractmethod
    async def validate_model(self, model: str) -> bool:
        """Check if model is available and accessible.

        Args:
            model: Model identifier

        Returns:
            True if model is valid and accessible

        Raises:
            IOError: If validation fails (API error)
        """
        pass

    @abstractmethod
    def estimate_tokens(self, text: str, model: str) -> int:
        """Estimate token count for text.

        Args:
            text: Input text
            model: Model identifier (different models have different tokenizers)

        Returns:
            Estimated token count

        Note:
            This is an approximation. Actual token count may differ slightly.
        """
        pass
