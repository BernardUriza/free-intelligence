"""LLM Service - Public API.

Main classes:
    from backend.services.llm import LLMModelService, PersonaManager
"""

from backend.services.llm.services.llm_model_service import LLMModelService
from backend.services.llm.services.persona.manager import PersonaManager

__all__ = ["LLMModelService", "PersonaManager"]
