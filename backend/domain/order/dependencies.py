"""FastAPI Dependency Injection providers for Order domain.

Provides dependency injection for order routers using FastAPI Depends().
Direct repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

# Import singleton factory from centralized location
from backend.infrastructure.common.repository_singletons import (
    get_task_repository,
)
