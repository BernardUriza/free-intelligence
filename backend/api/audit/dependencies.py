"""FastAPI Dependency Injection providers for Audit API.

Provides dependency injection for routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - API Layer DI
"""

from backend.utils.common.infrastructure.container import get_container


def get_audit_service():
    """Get audit service from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct service instantiation.

    Returns:
        AuditService instance
    """
    return get_container().get_audit_service()
