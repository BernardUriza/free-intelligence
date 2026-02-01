"""Interface for LLM Model Service - enables dependency injection.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Tierra (LLMModelService DI)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.models.llm_model import (
        LLMModel,
        LLMModelCreate,
        LLMModelUpdate,
        LLMProvider,
    )


class ILLMModelService(ABC):
    """Abstract interface for LLM model configuration management.

    This interface defines the contract for managing LLM model configurations.
    Services depend on this interface, not the concrete LLMModelService implementation.

    Key responsibilities:
    - CRUD operations for LLM models
    - Provider-based filtering
    - Cache management for config files
    """

    @abstractmethod
    def list_models(self, include_inactive: bool = False) -> list[LLMModel]:
        """List all LLM models.

        Args:
            include_inactive: Include inactive models in results

        Returns:
            List of LLMModel objects
        """
        pass

    @abstractmethod
    def get_model(self, model_id: str) -> LLMModel | None:
        """Get a specific model by ID.

        Args:
            model_id: Model identifier

        Returns:
            LLMModel or None if not found
        """
        pass

    @abstractmethod
    def create_model(self, data: LLMModelCreate) -> LLMModel:
        """Create a new LLM model.

        Args:
            data: Model creation data

        Returns:
            Created LLMModel

        Raises:
            ValueError: If model ID already exists
        """
        pass

    @abstractmethod
    def update_model(self, model_id: str, data: LLMModelUpdate) -> LLMModel | None:
        """Update an existing LLM model.

        Args:
            model_id: Model identifier
            data: Update data

        Returns:
            Updated LLMModel or None if not found
        """
        pass

    @abstractmethod
    def delete_model(self, model_id: str, hard_delete: bool = False) -> bool:
        """Delete or deactivate an LLM model.

        Args:
            model_id: Model identifier
            hard_delete: If True, permanently remove; otherwise soft delete

        Returns:
            True if operation succeeded
        """
        pass

    @abstractmethod
    def get_models_by_provider(self, provider: LLMProvider) -> list[LLMModel]:
        """Get all models from a specific provider.

        Args:
            provider: LLM provider

        Returns:
            List of models from that provider
        """
        pass
