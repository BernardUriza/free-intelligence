"""Infrastructure interfaces for Clean Architecture.

Defines abstract contracts for infrastructure components (workers, events, etc.).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from .iworker_pool import IWorkerPool

__all__ = [
    "IWorkerPool",
]
