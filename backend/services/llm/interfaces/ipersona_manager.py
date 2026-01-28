"""Persona manager interface.

Manages medical assistant personas and their configurations.
Decouples persona logic from storage implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IPersonaManager(ABC):
    """Persona configuration management.

    Responsibilities:
    - Load persona configurations (system prompts, personality traits)
    - Validate persona compatibility with models
    - Cache persona configs for performance
    - Support dynamic persona switching

    Persona Types:
    - medical_assistant: General medical consultation
    - specialist: Specific medical specialties (cardiology, neurology, etc.)
    - triage: Emergency triage assessment
    - educational: Patient education and explanations

    Clean Architecture Benefits:
    - Services don't know how personas are stored
    - Easy to test with mock personas
    - Can migrate from JSON files to database without changing services
    """

    @abstractmethod
    def get_persona(self, persona_id: str) -> Dict[str, Any]:
        """Retrieve persona configuration.

        Args:
            persona_id: Persona identifier (medical_assistant, specialist_cardiology, etc.)

        Returns:
            Dict with keys:
                - persona_id: str
                - name: str (human-readable name)
                - system_prompt: str (LLM system message)
                - temperature: float (default temperature)
                - max_tokens: int (default max tokens)
                - traits: Dict[str, Any] (personality traits)
                - supported_models: List[str] (compatible models)
                - metadata: Dict[str, Any] (custom fields)

        Raises:
            ValueError: If persona_id doesn't exist
        """
        pass

    @abstractmethod
    def list_personas(self) -> List[Dict[str, Any]]:
        """List all available personas.

        Returns:
            List of persona dicts (see get_persona for structure)
            Sorted by name
        """
        pass

    @abstractmethod
    def validate_persona_model(self, persona_id: str, model: str) -> bool:
        """Check if model is compatible with persona.

        Args:
            persona_id: Persona identifier
            model: Model identifier

        Returns:
            True if compatible, False otherwise

        Raises:
            ValueError: If persona_id doesn't exist
        """
        pass

    @abstractmethod
    def get_system_prompt(self, persona_id: str, context: Dict[str, Any] | None = None) -> str:
        """Get system prompt for persona with optional context interpolation.

        Args:
            persona_id: Persona identifier
            context: Optional variables to interpolate into prompt
                     (e.g., {"patient_name": "Juan", "specialty": "cardiology"})

        Returns:
            System prompt string with interpolated context

        Raises:
            ValueError: If persona_id doesn't exist or context variables are missing
        """
        pass

    @abstractmethod
    def create_persona(self, persona_config: Dict[str, Any]) -> str:
        """Create new persona.

        Args:
            persona_config: Persona configuration dict

        Returns:
            Created persona ID

        Raises:
            ValueError: If persona_config is invalid
            IOError: If storage operation fails
        """
        pass

    @abstractmethod
    def update_persona(self, persona_id: str, updates: Dict[str, Any]) -> bool:
        """Update persona configuration.

        Args:
            persona_id: Persona identifier
            updates: Dict of fields to update

        Returns:
            True if update successful, False if persona not found

        Raises:
            ValueError: If updates are invalid
            IOError: If storage operation fails
        """
        pass

    @abstractmethod
    def delete_persona(self, persona_id: str) -> bool:
        """Delete persona.

        Args:
            persona_id: Persona identifier

        Returns:
            True if deletion successful, False if persona not found

        Raises:
            IOError: If delete operation fails
        """
        pass
