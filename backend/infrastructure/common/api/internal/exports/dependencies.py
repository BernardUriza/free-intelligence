"""FastAPI Dependency Injection providers for Export API.

Provides dependency injection for export handlers using FastAPI Depends().
Direct service instantiation - no service locator (Phase 4B).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4B - Complete Service Locator Elimination
"""

from backend.services.audit.services.audit_service import AuditService
from backend.infrastructure.common.repository_singletons import (
    get_audit_repository,
)
from backend.infrastructure.common.services.export_service import ExportService


def get_audit_service() -> AuditService:
    """Get audit service - direct instantiation (Phase 4B).

    Returns:
        AuditService instance with injected AuditRepository

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return AuditService(repository=get_audit_repository())


def get_export_service() -> ExportService:
    """Get export service - direct instantiation (Phase 4B).

    Returns:
        ExportService instance with default configuration

    Configuration (explicit):
        export_dir: None → /tmp/fi_exports (via EXPORT_DIR env var)
        signing_key: None (no JWS signing)
        git_commit: "dev" (development mode)

    Note:
        No longer uses service locator (get_container).
        For custom config, instantiate ExportService directly with parameters.
    """
    return ExportService(
        export_dir=None,      # Uses EXPORT_DIR env var or /tmp/fi_exports
        signing_key=None,     # No signing in default config
        git_commit="dev",     # Development mode
    )
