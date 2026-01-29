"""FastAPI Dependency Injection providers for System API.

Provides dependency injection for system health router using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - Service Locator elimination
"""

from backend.services.system.system_health_service import DISystemHealthService
from backend.utils.common.infrastructure.container import get_container


def get_system_health_service() -> DISystemHealthService:
    """Get system health service from container.

    Note: This is a temporary bridge during migration.
    Eventually, SystemHealthService will use constructor injection.

    Returns:
        DISystemHealthService instance
    """
    return get_container().get_di_system_health_service()
