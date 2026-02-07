"""Diarization provider factory.

Factory Pattern + Registry Pattern for provider instantiation.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from typing import Any, Callable

from backend.providers.diarization.base import DiarizationProvider
from backend.providers.diarization.providers.azure_gpt4 import AzureGPT4Provider
from backend.providers.diarization.providers.deepgram import DeepgramProvider
from backend.providers.diarization.providers.pyannote import PyannoteProvider

# Provider registry - maps name to constructor
_PROVIDER_REGISTRY: dict[str, Callable[[dict[str, Any] | None], DiarizationProvider]] = {
    "pyannote": PyannoteProvider,
    "deepgram": DeepgramProvider,
    "azure_gpt4": AzureGPT4Provider,
}


def get_diarization_provider(
    provider_name: str,
    config: dict[str, Any] | None = None,
) -> DiarizationProvider:
    """Factory function to get diarization provider instance.

    Args:
        provider_name: "pyannote", "deepgram", or "azure_gpt4"
        config: Provider-specific configuration

    Returns:
        DiarizationProvider instance

    Raises:
        ValueError: If provider not supported
    """
    provider_ctor = _PROVIDER_REGISTRY.get(provider_name.lower())
    if not provider_ctor:
        supported = list(_PROVIDER_REGISTRY.keys())
        raise ValueError(
            f"Unknown diarization provider: {provider_name}. Supported: {supported}"
        )

    return provider_ctor(config)


def list_providers() -> list[str]:
    """List available provider names."""
    return list(_PROVIDER_REGISTRY.keys())


def register_provider(
    name: str,
    provider_class: Callable[[dict[str, Any] | None], DiarizationProvider],
) -> None:
    """Register a custom diarization provider.

    Useful for testing or extending with custom providers.

    Args:
        name: Provider identifier
        provider_class: Provider constructor
    """
    _PROVIDER_REGISTRY[name.lower()] = provider_class
