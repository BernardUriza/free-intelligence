"""Session Service - Business logic for medical sessions.

Handles session lifecycle:
- Session creation
- Status tracking (all task types)
- Session finalization
- Task aggregation

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-11-14 (complete task aggregation)
Card: Clean Architecture Refactor
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.utils.common.logging.logger import get_logger

# NOTE: Removed broken imports from infrastructure.storage.infrastructure.hdf5.task_repository
# Those functions (get_task_metadata, task_exists) don't exist in the codebase
# SessionService now relies on repository dependency injection instead

logger = get_logger(__name__)


class SessionService:
    """Service for medical session management.

    Provides unified view of session state across all task types.
    """

    def __init__(self, repository=None):
        """Initialize SessionService.

        Args:
            repository: SessionRepository instance (optional for backwards compatibility)
        """
        self.repository = repository

    async def get_session_info(self, session_id: str) -> dict:
        """Get session information from repository.

        Args:
            session_id: Session UUID

        Returns:
            dict with session metadata

        Raises:
            ValueError: If session not found
        """
        # Get session from repository
        if self.repository:
            session_data = self.repository.read(session_id)
        else:
            # Fallback: Direct HDF5 access
            from backend import SessionRepository
            from pathlib import Path

            storage_path = Path("storage/corpus.h5")
            repo = SessionRepository(storage_path)
            session_data = repo.read(session_id)

        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        # Extract metadata and add missing fields
        metadata = session_data.get("metadata", {})
        now = datetime.now(UTC).isoformat()

        return {
            "id": session_id,
            "session_id": session_id,
            "created_at": metadata.get("created_at", now),
            "updated_at": metadata.get("updated_at", now),
            "last_active": metadata.get("last_active", now),
            "interaction_count": metadata.get("interaction_count", 0),
            "status": session_data.get("status", "active"),
            "is_persisted": True,
            "owner_hash": metadata.get("user_id", ""),
            "thread_id": metadata.get("thread_id"),
        }

    def list_sessions(self, user_id: str | None = None) -> list[dict]:
        """List sessions with MANDATORY tenant isolation.

        SECURITY CRITICAL: This method enforces tenant isolation by filtering
        sessions by user_id (owner_hash). Calling without user_id returns
        ALL sessions (multi-tenant data leak).

        Args:
            user_id: User ID / owner_hash (REQUIRED for tenant isolation)

        Returns:
            List of session dictionaries with basic metadata

        Raises:
            ValueError: If user_id is None (tenant isolation violation)

        Example:
            sessions = service.list_sessions(user_id="sha256:abc123")
        """
        if not user_id:
            logger.error(
                "TENANT_ISOLATION_VIOLATION",
                message="list_sessions called without user_id",
                stack_trace=True,
            )
            raise ValueError(
                "user_id is REQUIRED for tenant isolation. "
                "Calling list_sessions() without user_id would return ALL sessions across ALL tenants, "
                "violating HIPAA/GDPR compliance."
            )

        # Use SessionRepository if available, otherwise fall back to direct HDF5 access
        if self.repository:
            sessions = self.repository.list_by_user_id(user_id=user_id, limit=100)
        else:
            # Fallback: Direct HDF5 access (for backwards compatibility)
            from backend import SessionRepository
            from backend.config import CORPUS_PATH

            repo = SessionRepository(CORPUS_PATH)
            sessions = repo.list_by_user_id(user_id=user_id, limit=100)

        logger.info(
            "SESSIONS_LISTED",
            user_id=user_id,
            count=len(sessions),
            filtered_by_owner=True,  # Explicit log for audit
        )

        return sessions

    def create_session(self, session_id: str, user_id: str, metadata: dict | None = None) -> dict:
        """Create new session with tenant isolation.

        Args:
            session_id: Unique session identifier
            user_id: User ID / owner (for tenant isolation)
            metadata: Optional session metadata

        Returns:
            Created session dict

        Raises:
            ValueError: If session already exists
        """
        if self.repository:
            self.repository.create(
                entity={
                    "session_id": session_id,
                    "user_id": user_id,
                    "metadata": metadata or {},
                }
            )
        else:
            # Fallback: Direct HDF5 access
            from backend import SessionRepository
            from pathlib import Path

            storage_path = Path("storage/corpus.h5")
            repo = SessionRepository(storage_path)
            repo.create(
                entity={
                    "session_id": session_id,
                    "user_id": user_id,
                    "metadata": metadata or {},
                }
            )

        logger.info("SESSION_CREATED", session_id=session_id, user_id=user_id)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
        }

    def update_session(
        self, session_id: str, status: str | None = None, interaction_count: int | None = None
    ) -> bool:
        """Update session metadata.

        Args:
            session_id: Session identifier
            status: New status (optional)
            interaction_count: New interaction count (optional)

        Returns:
            True if update successful
        """
        metadata = {}
        if status:
            metadata["status"] = status
        if interaction_count is not None:
            metadata["interaction_count"] = interaction_count

        if self.repository:
            success = self.repository.update(
                entity_id=session_id, entity={"metadata": metadata}
            )
        else:
            # Fallback: Direct HDF5 access
            from backend import SessionRepository
            from pathlib import Path

            storage_path = Path("storage/corpus.h5")
            repo = SessionRepository(storage_path)
            success = repo.update(entity_id=session_id, entity={"metadata": metadata})

        if success:
            logger.info("SESSION_UPDATED", session_id=session_id)

        return success
