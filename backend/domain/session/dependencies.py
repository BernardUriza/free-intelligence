"""FastAPI Dependency Injection providers for Session domain.

Provides dependency injection for session routers using FastAPI Depends().
Direct repository/service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from backend.services.audit.services.audit_service import AuditService

# Import singleton factories from centralized location
from backend.infrastructure.common.repository_singletons import (
    get_audit_repository,
    get_corpus_repository,
    get_task_repository,
)


def get_audit_service() -> AuditService:
    """Get audit service - direct instantiation (Phase 4A).

    Returns:
        AuditService instance with injected AuditRepository

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return AuditService(repository=get_audit_repository())


def get_session_service() -> "SessionService":
    """Get session service - direct instantiation (Phase 4B fix).

    Returns:
        SessionService instance with injected repository dependencies

    Note:
        SessionService was NEVER removed, just the dependency function was deleted.
        This function restores FastAPI Depends() compatibility for routers.
    """
    from backend.domain.session.services.session_service import SessionService
    # SessionService accepts optional repository but can work without it (legacy compat)
    return SessionService(repository=None)
