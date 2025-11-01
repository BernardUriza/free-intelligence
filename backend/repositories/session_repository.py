"""Repository for session data operations.

Handles session lifecycle management - creation, updates, and queries.
Separates session persistence logic from business logic.

Clean Code: Abstraction - hides HDF5 complexity behind simple interface.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import h5py

from .base_repository import BaseRepository
from backend.types import JobStatusDict

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository):
    """Repository for session management.

    Responsibilities:
    - Create and retrieve sessions
    - Track session status (pending, active, completed, failed)
    - Store session metadata and configuration
    """

    SESSIONS_GROUP = "sessions"
    METADATA_GROUP = "metadata"

    def __init__(self, h5_file_path: str | Path) -> None:
        """Initialize session repository."""
        super().__init__(h5_file_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure required HDF5 structure exists."""
        try:
            with self._open_file("a") as f:
                f.require_group(self.SESSIONS_GROUP)
                f.require_group(self.METADATA_GROUP)
            logger.info("SESSION_STRUCTURE_READY", path=str(self.h5_file_path))
        except OSError as e:
            logger.error("SESSION_STRUCTURE_INIT_FAILED", error=str(e))
            raise

    def create(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create new session.

        Args:
            session_id: Unique session identifier
            user_id: Optional user identifier
            metadata: Session metadata (config, settings, etc.)

        Returns:
            Session ID

        Raises:
            ValueError: If session_id is empty or already exists
            IOError: If HDF5 operation fails
        """
        if not session_id:
            raise ValueError("session_id is required")

        try:
            with self._open_file("r+") as f:
                sessions_group = f[self.SESSIONS_GROUP]

                if session_id in sessions_group:
                    raise ValueError(f"Session {session_id} already exists")

                # Create session group
                session_group = sessions_group.create_group(session_id)

                # Store basic session info
                session_group.attrs["created_at"] = datetime.now(timezone.utc).isoformat()
                session_group.attrs["status"] = "active"
                if user_id:
                    session_group.attrs["user_id"] = user_id

                # Store metadata
                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            session_group.attrs[key] = value
                        elif isinstance(value, (list, dict)):
                            session_group.attrs[key] = json.dumps(value)

            self._log_operation("create", session_id)
            return session_id

        except Exception as e:
            self._log_operation("create", session_id, status="failed", error=str(e))
            raise

    def read(self, session_id: str) -> Optional[dict[str, Any]]:
        """Read session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data with metadata, or None if not found
        """
        try:
            with self._open_file("r") as f:
                if session_id not in f[self.SESSIONS_GROUP]:
                    return None

                session_group = f[self.SESSIONS_GROUP][session_id]
                metadata = dict(session_group.attrs)

                return {
                    "session_id": session_id,
                    "metadata": metadata,
                    "status": metadata.get("status", "unknown"),
                }

        except Exception as e:
            logger.error("SESSION_READ_FAILED", session_id=session_id, error=str(e))
            return None

    def update(
        self,
        session_id: str,
        status: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Update session status and metadata.

        Args:
            session_id: Session identifier
            status: New status (active, completed, failed)
            metadata: Updated metadata

        Returns:
            True if update successful
        """
        try:
            with self._open_file("r+") as f:
                if session_id not in f[self.SESSIONS_GROUP]:
                    return False

                session_group = f[self.SESSIONS_GROUP][session_id]

                if status:
                    session_group.attrs["status"] = status

                if metadata:
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            session_group.attrs[key] = value
                        elif isinstance(value, (list, dict)):
                            session_group.attrs[key] = json.dumps(value)

                session_group.attrs["updated_at"] = datetime.now(timezone.utc).isoformat()

            self._log_operation("update", session_id)
            return True

        except Exception as e:
            self._log_operation("update", session_id, status="failed", error=str(e))
            return False

    def delete(self, session_id: str) -> bool:
        """Delete session (marks as deleted).

        Args:
            session_id: Session identifier

        Returns:
            True if deletion successful
        """
        try:
            with self._open_file("r+") as f:
                if session_id not in f[self.SESSIONS_GROUP]:
                    return False

                session_group = f[self.SESSIONS_GROUP][session_id]
                session_group.attrs["status"] = "deleted"
                session_group.attrs["deleted_at"] = datetime.now(timezone.utc).isoformat()

            self._log_operation("delete", session_id)
            return True

        except Exception as e:
            self._log_operation("delete", session_id, status="failed", error=str(e))
            return False

    def list_all(self, limit: Optional[int] = None, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List sessions with optional filtering.

        Args:
            limit: Maximum sessions to return
            status: Filter by status (active, completed, failed, deleted)

        Returns:
            List of sessions
        """
        try:
            with self._open_file("r") as f:
                sessions_group = f[self.SESSIONS_GROUP]
                session_ids = list(sessions_group.keys())

                if limit:
                    session_ids = session_ids[:limit]

                results = []
                for session_id in session_ids:
                    session_data = self.read(session_id)
                    if session_data:
                        if status is None or session_data.get("status") == status:
                            if session_data.get("status") != "deleted":
                                results.append(session_data)

                return results

        except Exception as e:
            logger.error("SESSION_LIST_FAILED", error=str(e))
            return []
