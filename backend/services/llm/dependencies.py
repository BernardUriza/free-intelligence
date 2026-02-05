"""FastAPI Dependency Injection providers for LLM service.

Provides dependency injection for routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.repositories.audit_repository import AuditRepository
    from backend.policy.interfaces.ipolicy_loader import IPolicyLoader
    from backend.services.llm.interfaces.illm_model_service import ILLMModelService

from backend.services.audit.services.audit_service import AuditService
from backend.infrastructure.common.repository_singletons import (
    get_audit_repository,
)
# Note: get_policy_loader_dep imported lazily in get_chat_service to avoid circular import
from backend.services.llm.services.di_chat_service import DIChatService
from backend.services.llm.services.persona.manager import PersonaManager
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


def get_audit_service(
    audit_repo: AuditRepository | None = None,
) -> AuditService:
    """Get audit service with injected dependencies.

    Args:
        audit_repo: Audit repository (optional, uses default)

    Returns:
        AuditService instance
    """
    audit_repo = audit_repo or get_audit_repository()
    return AuditService(audit_repo)


@lru_cache(maxsize=1)
def _get_persona_manager_singleton() -> PersonaManager:
    """Internal singleton factory for PersonaManager.

    Uses @lru_cache to ensure only ONE instance is created,
    loading YAML configuration only once per process.

    Returns:
        PersonaManager singleton instance with YAML loaded
    """
    return PersonaManager()


def get_persona_manager() -> PersonaManager:
    """Get persona manager singleton.

    Returns:
        PersonaManager singleton instance (shared across all callers)

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.

    Performance:
        YAML parsing happens only on first call.
        Subsequent calls return the cached singleton.
    """
    return _get_persona_manager_singleton()


def get_llm_logger() -> ILogger:
    """Get logger for LLM service.

    Returns:
        ILogger instance
    """
    return get_logger("llm")


def get_chat_service(
    persona_manager: PersonaManager | None = None,
    audit_service: AuditService | None = None,
    policy_loader: "IPolicyLoader | None" = None,
    logger: ILogger | None = None,
) -> DIChatService:
    """Get chat service with injected dependencies.

    FastAPI provider for DIChatService.

    Args:
        persona_manager: Persona manager (optional, uses default)
        audit_service: Audit service (optional, uses default)
        policy_loader: Policy loader (optional, uses default)
        logger: Logger instance (optional, uses default)

    Returns:
        DIChatService instance
    """
    from backend.infrastructure.common.policy_provider import get_policy_loader_dep

    persona_manager = persona_manager or get_persona_manager()
    audit_service = audit_service or get_audit_service()
    policy_loader = policy_loader or get_policy_loader_dep()
    logger = logger or get_llm_logger()

    return DIChatService(
        persona_manager=persona_manager,
        audit_service=audit_service,
        policy_loader=policy_loader,
        logger=logger,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM MODEL SERVICE FACTORY (Phase 2.3 - Extracted from workflow)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@lru_cache(maxsize=1)
def _get_llm_model_service_singleton() -> "ILLMModelService":
    """Internal singleton factory for LLMModelService."""
    from backend.services.llm.services.llm_model_service import LLMModelService

    return LLMModelService()


def get_llm_model_service_dep() -> "ILLMModelService":
    """Get LLM model service singleton for model catalog management.

    Returns:
        ILLMModelService singleton instance

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.
    """
    return _get_llm_model_service_singleton()


__all__ = [
    "get_audit_service",
    "get_persona_manager",
    "get_llm_logger",
    "get_chat_service",
    "get_llm_model_service_dep",
]
