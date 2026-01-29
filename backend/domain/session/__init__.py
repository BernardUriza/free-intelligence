"""Session domain module - pure business logic.

Exports:
- Session: Domain entity
- SessionStatus: Status enum
- ISessionRepository: Repository interface

Author: Claude Code
Created: 2026-01-28
"""

from backend.domain.session.entity import Session, SessionStatus
from backend.domain.session.repository import ISessionRepository

__all__ = ["Session", "SessionStatus", "ISessionRepository"]
