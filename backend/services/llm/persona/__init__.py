"""
Persona Module - Free Intelligence v2.0

Modular architecture for persona management:
- exceptions: Custom error types
- schemas: Pydantic validation models
- config: Immutable runtime configuration
- prompt_builder: Secure prompt construction with RAG
- router: Message-to-persona routing
- manager: Main PersonaManager class

Usage:
    from backend.services.llm.persona import PersonaManager, PersonaConfig, PersonaNotFound

Aurity-Prompt-ID: AUR-PERSONA-MODULE-2.0
"""

from .config import CacheEntry, PersonaConfig
from .constants import DEFAULT_CACHE_TTL_S, DEFAULT_MAX_RAG_CHARS, MODE_MARKERS
from .exceptions import PersonaConfigInvalid, PersonaError, PersonaNotFound
from .manager import PersonaManager
from .prompt_builder import PromptBuilder
from .router import PersonaRouter
from .schemas import PersonaTemplateModel

__all__ = [
    # Exceptions
    "PersonaError",
    "PersonaNotFound",
    "PersonaConfigInvalid",
    # Schemas
    "PersonaTemplateModel",
    # Config
    "PersonaConfig",
    "CacheEntry",
    # Constants
    "DEFAULT_CACHE_TTL_S",
    "DEFAULT_MAX_RAG_CHARS",
    "MODE_MARKERS",
    # Classes
    "PromptBuilder",
    "PersonaRouter",
    "PersonaManager",
]
