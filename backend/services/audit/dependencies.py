"""FastAPI Dependency Injection providers for Audit service.

Provides singleton AuditService dependency.

Author: Claude Code
Created: 2026-02-02 (Phase 2.3 - DI Refactor - Circular Import Fix)
"""

from __future__ import annotations

from functools import lru_cache

from backend.services.audit.services.audit_service import AuditService
from backend.infrastructure.common.repository_singletons import get_audit_repository


@lru_cache(maxsize=1)
def _get_audit_service_singleton() -> AuditService:
    """Internal singleton factory for AuditService."""
    return AuditService(repository=get_audit_repository())


def get_audit_service_dep() -> AuditService:
    """Get audit service singleton (Phase 4A + DI Refactor).

    Returns:
        AuditService singleton instance with injected AuditRepository

    Thread Safety:
        @lru_cache is thread-safe in Python 3.9+.

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return _get_audit_service_singleton()


__all__ = ["get_audit_service_dep"]
