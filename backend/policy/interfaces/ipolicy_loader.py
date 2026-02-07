"""Interface for PolicyLoader - enables dependency injection.

This interface defines the contract for accessing policy configuration.
Workers depend on this interface, not the concrete PolicyLoader implementation.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Eliminate Service Locator
Updated: 2026-02-01 (Phase 2.3 Urano - added policy/policy_path for API router)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class IPolicyLoader(ABC):
    """Abstract interface for policy configuration access.

    This interface exposes only the methods needed by workers:
    - get_diarization_config(): For diarization_worker
    - get_llm_config(): For soap_worker

    By depending on this interface instead of the concrete PolicyLoader,
    workers become easier to test (mock the interface) and more loosely coupled.

    Attributes:
        policy: The full loaded policy dictionary (None if not loaded)
        policy_path: Path to the policy YAML file
    """

    # Instance attributes (not abstract - implementations set these in __init__)
    policy: dict[str, Any] | None
    policy_path: Path

    @abstractmethod
    def get_diarization_config(self) -> dict[str, Any]:
        """Get diarization configuration section.

        Returns:
            Dict with diarization configuration including:
            - primary_provider: str
            - fallback_providers: list[str]
            - providers: dict with provider configs

        Raises:
            RuntimeError: If policy not loaded
        """
        pass

    @abstractmethod
    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM configuration section.

        Returns:
            Dict with LLM configuration including:
            - primary_provider: str
            - fallback_provider: str
            - providers: dict with provider configs

        Raises:
            RuntimeError: If policy not loaded
        """
        pass

    @abstractmethod
    def get_primary_provider(self) -> str:
        """Get primary LLM provider name.

        Returns:
            Provider name (e.g., "claude", "ollama")
        """
        pass

    @abstractmethod
    def get_primary_diarization_provider(self) -> str:
        """Get primary diarization provider name.

        Returns:
            Provider name (e.g., "azure_gpt4", "pyannote")
        """
        pass
