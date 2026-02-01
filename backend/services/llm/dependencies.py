"""FastAPI Dependency Injection providers for LLM service.

Provides dependency injection for routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (TODO cleanup - use centralized config)
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from pathlib import Path

from backend.api.audit.services.audit_service import AuditService
from backend.config import CORPUS_PATH
from backend.policy.policy_loader import PolicyLoader, get_policy_loader
from backend.repositories.audit_repository import AuditRepository
from backend.services.llm.services.di_chat_service import DIChatService
from backend.services.llm.services.persona_manager import PersonaManager
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


def get_corpus_path() -> str:
    """Get HDF5 corpus path from centralized config.

    Returns:
        Path to corpus.h5 file as string
    """
    return str(CORPUS_PATH)


def get_audit_repository() -> AuditRepository:
    """Get audit repository from corpus path.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        AuditRepository instance
    """
    corpus_path = Path(get_corpus_path())
    return AuditRepository(corpus_path)


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


def get_persona_manager() -> PersonaManager:
    """Get persona manager singleton.

    Note: PersonaManager is already a singleton (loads YAML config once).
    This provider just returns the instance.

    Returns:
        PersonaManager instance
    """
    return PersonaManager()


def get_llm_logger() -> ILogger:
    """Get logger for LLM service.

    Returns:
        ILogger instance
    """
    return get_logger("llm")


def get_chat_service(
    persona_manager: PersonaManager | None = None,
    audit_service: AuditService | None = None,
    policy_loader: PolicyLoader | None = None,
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
    persona_manager = persona_manager or get_persona_manager()
    audit_service = audit_service or get_audit_service()
    policy_loader = policy_loader or get_policy_loader()
    logger = logger or get_llm_logger()

    return DIChatService(
        persona_manager=persona_manager,
        audit_service=audit_service,
        policy_loader=policy_loader,
        logger=logger,
    )
