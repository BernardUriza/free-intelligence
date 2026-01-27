"""LLM Service - Public API.

Main classes:
    from backend.core.services.llm import LLMModelService, PersonaManager
"""

from backend.core.services.llm.services.llm_model_service import LLMModelService
from backend.core.services.llm.services.persona_manager import PersonaManager

__all__ = ["LLMModelService", "PersonaManager"]
