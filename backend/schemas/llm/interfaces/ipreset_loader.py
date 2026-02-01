"""Interface for PresetLoader - enables dependency injection.

This interface defines the contract for loading LLM presets.
Workers depend on this interface, not the concrete PresetLoader implementation.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Eliminate Service Locator
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.schemas.llm.preset_loader import PresetConfig


class IPresetLoader(ABC):
    """Abstract interface for LLM preset loading.

    This interface exposes only the methods needed by workers:
    - load_preset(): Load a preset configuration by ID

    Used by:
        - emotion_worker: loads "emotion_analyzer" preset
    """

    @abstractmethod
    def load_preset(self, preset_id: str) -> "PresetConfig":
        """Load preset from YAML file.

        Args:
            preset_id: Preset identifier (e.g., "emotion_analyzer", "soap_generator")

        Returns:
            PresetConfig object with LLM configuration

        Raises:
            FileNotFoundError: If preset file not found
            ValueError: If preset YAML is invalid
        """
        pass

    @abstractmethod
    def list_presets(self) -> list[str]:
        """List available preset IDs.

        Returns:
            List of preset IDs (filenames without .yaml)
        """
        pass
