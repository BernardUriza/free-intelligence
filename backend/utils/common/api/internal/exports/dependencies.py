"""FastAPI Dependency Injection providers for Export API.

Provides dependency injection for export handlers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - Service Locator elimination
"""

from backend.api.audit.services.audit_service import AuditService
from backend.container import get_container
from backend.utils.common.services.export_service import ExportService


def get_export_service() -> ExportService:
    """Get export service from container.

    Note: This is a temporary bridge during migration.
    Eventually, ExportService will use constructor injection.

    Returns:
        ExportService instance
    """
    return get_container().get_export_service()


def get_audit_service() -> AuditService:
    """Get audit service from container.

    Note: This is a temporary bridge during migration.
    Eventually, AuditService will be injected directly.

    Returns:
        AuditService instance
    """
    return get_container().get_audit_service()
