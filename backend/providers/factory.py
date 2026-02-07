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
        provider_name: "ollama" (only supported provider - routes to FI Local via tunnel)
        config: Provider-specific configuration

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider not supported

    Example:
        >>> provider = get_provider("ollama", {"model": "qwen3:1.7b"})
        >>> response = provider.generate("Hello!")

    Note:
        Cloud backend only supports Ollama (routed to FI Local GPU via Cloudflare Tunnel).
        Direct API calls to Claude/Azure are removed for PHI compliance.
    """
    # Import providers lazily to avoid circular imports
    from backend.providers.ollama import OllamaProvider

    provider_map: dict[str, Callable[[dict[str, Any] | None], LLMProvider]] = {
        "ollama": OllamaProvider,
    }

    provider_ctor = provider_map.get(provider_name.lower())
    if not provider_ctor:
        raise ValueError(
            f"Unknown provider: {provider_name}. " + f"Supported: {list(provider_map.keys())}"
        )

    return provider_ctor(config)
