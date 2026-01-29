"""Session repository interface - domain contract.

Defines the contract for session persistence operations.
Implementation uses HDF5 task-based schema.

This interface is FRAMEWORK-AGNOSTIC.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from backend.domain.session.entity import Session, SessionStatus


class ISessionRepository(ABC):
    """Interface for session persistence operations.

    Implementations:
    - HDF5SessionRepository (current: task-based schema)
    - InMemorySessionRepository (for testing)
    """

    @abstractmethod
    def save(self, session: Session) -> str:
        """Persist session entity.

        Args:
            session: Session entity to save

        Returns:
            session_id of saved entity

        Raises:
            RepositoryError: If persistence fails
        """
        pass

    @abstractmethod
    def find_by_id(self, session_id: str) -> Session | None:
        """Find session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Session entity if found, None otherwise
        """
        pass

    @abstractmethod
    def find_by_owner(
        self, owner_hash: str, limit: int = 100, offset: int = 0
    ) -> List[Session]:
        """Find sessions by owner.

        Args:
            owner_hash: Owner identifier (hashed user ID)
            limit: Maximum sessions to return
            offset: Number of sessions to skip

        Returns:
            List of Session entities
        """
        pass

    @abstractmethod
    def find_by_status(
        self, status: SessionStatus, limit: int = 100
    ) -> List[Session]:
        """Find sessions by status.

        Args:
            status: Session status to filter
            limit: Maximum sessions to return

        Returns:
            List of Session entities
        """
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List[Session]:
        """List all sessions with pagination.

        Args:
            limit: Maximum sessions to return
            offset: Number of sessions to skip

        Returns:
            List of Session entities (newest first)
        """
        pass

    @abstractmethod
    def update(self, session: Session) -> bool:
        """Update existing session.

        Args:
            session: Session entity with updated data

        Returns:
            True if update successful

        Raises:
            SessionNotFoundError: If session_id doesn't exist
            RepositoryError: If update fails
        """
        pass

    @abstractmethod
    def delete(self, session_id: str) -> bool:
        """Delete session by ID.

        Args:
            session_id: Session UUID

        Returns:
            True if deletion successful

        Note:
            Actual behavior (soft delete vs hard delete) depends on implementation
        """
        pass

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session UUID

        Returns:
            True if session exists
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Count total number of sessions.

        Returns:
            Total session count
        """
        pass

    @abstractmethod
    def count_by_status(self, status: SessionStatus) -> int:
        """Count sessions by status.

        Args:
            status: Session status to filter

        Returns:
            Count of sessions with given status
        """
        pass
