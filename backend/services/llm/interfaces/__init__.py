"""LLM service interfaces for Clean Architecture.

Defines abstract contracts for LLM providers and persona management.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from .iconversation_memory import IConversationMemory
from .illm_client import ILLMClient
from .ipersona_manager import IPersonaManager

__all__ = [
    "ILLMClient",
    "IPersonaManager",
    "IConversationMemory",
]
