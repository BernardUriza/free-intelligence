"""Domain Layer - Pure domain interfaces and entities.

Zero infrastructure dependencies.
Defines contracts for persistence without specifying implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.4 - Domain Layer
"""

from backend.domain.patient import IPatientRepository
from backend.domain.session import ISessionRepository

__all__ = [
    "IPatientRepository",
    "ISessionRepository",
]
