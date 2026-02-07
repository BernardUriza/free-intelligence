"""
Free Intelligence - LLM Provider Factory

Factory function to create LLM provider instances.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.providers.base import LLMProvider


def get_provider(provider_name: str, config: dict[str, Any] | None = None) -> LLMProvider:
    """
    Factory function to get LLM provider instance.

    Args:
        provider_name: "claude", "ollama", or "azure"
        config: Provider-specific configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider not supported

    Example:
        >>> provider = get_provider("ollama", {"model": "qwen3:1.7b"})
        >>> response = provider.generate("Hello!")
    """
    # Import providers lazily to avoid circular imports
    from backend.providers.azure_openai import AzureOpenAIProvider
    from backend.providers.claude import ClaudeProvider
    from backend.providers.ollama import OllamaProvider

    provider_map: dict[str, Callable[[dict[str, Any] | None], LLMProvider]] = {
        "claude": ClaudeProvider,
        "ollama": OllamaProvider,
        "azure": AzureOpenAIProvider,
        # "openai": OpenAIProvider,  # Future
    }

    provider_ctor = provider_map.get(provider_name.lower())
    if not provider_ctor:
        raise ValueError(
            f"Unknown provider: {provider_name}. " + f"Supported: {list(provider_map.keys())}"
        )

    return provider_ctor(config)
