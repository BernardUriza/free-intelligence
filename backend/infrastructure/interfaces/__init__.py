"""Infrastructure interfaces for Clean Architecture.

Defines abstract contracts for infrastructure components (events, logging, etc.).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from .ievent_bus import IEventBus
from .ilogger import ILogger

__all__ = [
    "IEventBus",
    "ILogger",
]
