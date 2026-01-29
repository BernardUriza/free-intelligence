"""FastAPI Dependency Injection providers for System API.

Provides dependency injection for system health router using FastAPI Depends().
Direct service instantiation - no service locator (Phase 4B).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-28 (Phase 4B - eliminate get_container)
Card: Backend Refactor Phase 4B - Complete Service Locator Elimination
"""

from backend.utils.common.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger
from backend.utils.system.services.di_system_health_service import DISystemHealthService


def get_system_logger() -> ILogger:
    """Get logger for system health service.

    Returns:
        ILogger instance
    """
    return get_logger("system")


def get_system_health_service() -> DISystemHealthService:
    """Get system health service - direct instantiation (Phase 4B).

    Returns:
        DISystemHealthService instance with injected logger

    Note:
        No longer uses service locator (get_container).
        Direct instantiation with logger injection.
    """
    return DISystemHealthService(logger=get_system_logger())
