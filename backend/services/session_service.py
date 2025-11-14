"""Service layer for session management.

Handles session lifecycle, state transitions, and coordination.

Clean Code: Business rules for sessions are encapsulated here,
not scattered across multiple endpoint handlers.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.logger import get_logger
from backend.repositories import SessionRepository

logger = get_logger(__name__)


class SessionService:
    """Service for session lifecycle management.

    Responsibilities:
    - Create and initialize sessions
    - Manage session state transitions (active -> completed/failed)
    - Track session metadata and configuration
    """

    # Valid session states
    VALID_STATES = {"active", "completed", "failed", "deleted"}

    def __init__(self, repository: SessionRepository) -> None:
        """Initialize service with repository dependency.

        Args:
            repository: SessionRepository instance for data access
        """
        self.repository = repository

    def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        config: dict[str, Any | None] | None = None,
    ) -> dict[str, Any]:
        """Create new session with validation.

        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            config: Session configuration

        Returns:
            Created session data

        Raises:
            ValueError: If session_id is invalid
            IOError: If storage fails
        """
        if not session_id or len(session_id) < 3:
            raise ValueError("session_id must be at least 3 characters")

        try:
            session_data: dict[str, Any | None] = {
                "session_id": session_id,
                "user_id": user_id,
                "metadata": config or {},
            }
            session_id = self.repository.create(session_data)

            logger.info("SESSION_CREATED", session_id=session_id, user_id=user_id)

            return {
                "session_id": session_id,
                "status": "active",
                "user_id": user_id,
            }

        except ValueError as e:
            logger.warning("SESSION_CREATION_VALIDATION_FAILED", error=str(e))
            raise
        except OSError as e:
            logger.error("SESSION_CREATION_FAILED", error=str(e))
            raise

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        try:
            return self.repository.read(session_id)
        except OSError as e:
            logger.error("SESSION_RETRIEVAL_FAILED", session_id=session_id, error=str(e))
            raise

    def update_session_status(
        self,
        session_id: str,
        status: str,
        details: dict[str, Any | None] | None = None,
    ) -> bool:
        """Update session status with validation.

        Args:
            session_id: Session identifier
            status: New status (active, completed, failed)
            details: Additional details about status change

        Returns:
            True if update successful

        Raises:
            ValueError: If status is invalid
        """
        if status not in self.VALID_STATES:
            raise ValueError(f"Invalid status. Must be one of: {self.VALID_STATES}")

        try:
            entity: dict[str, Any | None] = {
                "status": status,
                "metadata": details or {},
            }
            success = self.repository.update(session_id, entity)

            if success:
                logger.info("SESSION_STATUS_UPDATED", session_id=session_id, status=status)

            return success

        except ValueError as e:
            logger.warning("SESSION_UPDATE_VALIDATION_FAILED", error=str(e))
            raise
        except OSError as e:
            logger.error("SESSION_UPDATE_FAILED", session_id=session_id, error=str(e))
            raise

    def complete_session(
        self,
        session_id: str,
        result: dict[str, Any | None] | None = None,
    ) -> bool:
        """Mark session as completed successfully.

        Args:
            session_id: Session identifier
            result: Final result data

        Returns:
            True if session marked as completed
        """
        details = {"result": result} if result else {}
        return self.update_session_status(session_id, "completed", details)

    def fail_session(
        self,
        session_id: str,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> bool:
        """Mark session as failed.

        Args:
            session_id: Session identifier
            error: Error message
            error_code: Error code for categorization

        Returns:
            True if session marked as failed
        """
        details = {}
        if error:
            details["error"] = error
        if error_code:
            details["error_code"] = error_code

        return self.update_session_status(session_id, "failed", details)

    def list_sessions(
        self,
        limit: Optional[int] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List sessions with optional filtering.

        Args:
            limit: Maximum sessions to return
            user_id: Filter by user
            status: Filter by status

        Returns:
            List of sessions
        """
        sessions = self.repository.list_all(limit=limit, status=status)

        if user_id:
            sessions = [s for s in sessions if s.get("metadata", {}).get("user_id") == user_id]

        return sessions

    def end_session(self, session_id: str) -> bool:
        """Mark session as ended (soft delete).

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        try:
            success = self.repository.delete(session_id)
            if success:
                logger.info("SESSION_ENDED", session_id=session_id)
            return success
        except OSError as e:
            logger.error("SESSION_DELETION_FAILED", session_id=session_id, error=str(e))
            raise
