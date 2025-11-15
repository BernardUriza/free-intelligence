"""Repository for session data operations.

Handles session lifecycle management - creation, updates, and queries.
Separates session persistence logic from business logic.

Clean Code: Abstraction - hides HDF5 complexity behind simple interface.

SOLID Principles Applied:
- Single Responsibility: Each method handles one specific operation
- Open/Closed: Extensible serialization via _serialize/_deserialize helpers
- Dependency Inversion: Type hints define clear contracts

DRY Principle:
- Centralized serialization/deserialization in private helper methods
- No code duplication between create() and update()
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.logger import get_logger

from .base_repository import BaseRepository

logger = get_logger(__name__)


class SessionRepository(BaseRepository):
    """Repository for session management.

    Responsibilities:
    - Create and retrieve sessions
    - Track session status (pending, active, completed, failed)
    - Store session metadata and configuration
    """

    SESSIONS_GROUP = "sessions"
    METADATA_GROUP = "metadata"

    def __init__(self, h5_file_path: Union[str, Path]) -> None:
        """Initialize session repository."""
        super().__init__(h5_file_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure required HDF5 structure exists."""
        try:
            with self._open_file("a") as f:
                f.require_group(self.SESSIONS_GROUP)  # type: ignore[attr-defined]
                f.require_group(self.METADATA_GROUP)  # type: ignore[attr-defined]
            logger.info("SESSION_STRUCTURE_READY", file_path=str(self.h5_file_path))
        except OSError as e:
            logger.error("SESSION_STRUCTURE_INIT_FAILED", error=str(e))
            raise

    # ============================================================================
    # Private Helper Methods (DRY Principle)
    # ============================================================================

    @staticmethod
    def _serialize_value(value: Any) -> Union[str, int, float] | bool:
        """Serialize Python value to HDF5-compatible type.

        HDF5 attrs support: str, int, float, bool, bytes, numpy arrays
        Complex types (dict, list, None) → JSON string

        Best Practice (from web search):
        - JSON is recommended for dict serialization in HDF5
        - Maintains interoperability across systems
        - Human-readable format

        Args:
            value: Python value (any type)

        Returns:
            HDF5-compatible value (primitive or JSON string)
        """
        if isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (list, dict)) or value is None:
            # Serialize to JSON with marker prefix for safe deserialization
            return json.dumps(value)
        else:
            # Fallback: convert to string representation
            return str(value)

    @staticmethod
    def _deserialize_value(value: Any) -> Any:
        """Deserialize HDF5 attr value to Python type.

        Automatically detects JSON strings and deserializes them.
        Primitives pass through unchanged.

        Best Practice (from web search):
        - Symmetric serialization/deserialization
        - Auto-detection of JSON format
        - Graceful fallback for malformed data

        Args:
            value: HDF5 attr value (str, int, float, bool, bytes)

        Returns:
            Original Python type (dict, list, primitive, None)
        """
        # Pass through primitives (non-string types)
        if not isinstance(value, (str, bytes)):
            return value

        # Decode bytes to string
        if isinstance(value, bytes):
            value = value.decode("utf-8")

        # Try to deserialize JSON strings
        if isinstance(value, str):
            # Quick heuristic: JSON objects/arrays start with { or [
            if value.startswith(("{", "[")):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Not valid JSON, return as-is
                    return value
            # Check for JSON null
            elif value == "null":
                return None

        return value

    def _serialize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Serialize entire metadata dict for HDF5 storage.

        Single Responsibility: Handle all metadata serialization logic.

        Args:
            metadata: Raw metadata dict

        Returns:
            HDF5-compatible metadata dict
        """
        return {key: self._serialize_value(val) for key, val in metadata.items()}

    def _deserialize_metadata(self, attrs_dict: dict[str, Any]) -> dict[str, Any]:
        """Deserialize HDF5 attrs dict to Python types.

        Single Responsibility: Handle all metadata deserialization logic.

        Args:
            attrs_dict: Raw HDF5 attrs dict

        Returns:
            Python-native metadata dict (with dicts/lists restored)
        """
        return {key: self._deserialize_value(val) for key, val in attrs_dict.items()}

    # ============================================================================
    # Public CRUD Methods
    # ============================================================================

    def create(self, entity: dict[str, Optional[Any]], **kwargs: Any) -> str:
        """Create new session.

        Args:
            entity: Dict with 'session_id', 'user_id', 'metadata' keys

        Returns:
            Session ID

        Raises:
            ValueError: If session_id is empty or already exists
            IOError: If HDF5 operation fails
        """
        session_id = entity.get("session_id", "")
        user_id = entity.get("user_id")
        metadata = entity.get("metadata")

        if not session_id:
            raise ValueError("session_id is required")

        try:
            with self._open_file("r+") as f:
                sessions_group = f[self.SESSIONS_GROUP]

                if session_id in sessions_group:
                    raise ValueError(f"Session {session_id} already exists")

                # Create session group
                session_group = sessions_group.create_group(session_id)  # type: ignore[attr-defined]

                # Store basic session info
                session_group.attrs["created_at"] = datetime.now(timezone.utc).isoformat()
                session_group.attrs["status"] = "active"
                if user_id:
                    session_group.attrs["user_id"] = user_id

                # Store metadata (DRY: use _serialize_metadata helper)
                if metadata:
                    serialized_metadata = self._serialize_metadata(metadata)
                    for key, value in serialized_metadata.items():
                        session_group.attrs[key] = value

            self._log_operation("create", session_id)
            return session_id

        except Exception as e:
            self._log_operation("create", session_id, status="failed", error=str(e))
            raise

    def read(self, entity_id: str) -> dict[str, Any] | None:
        """Read session data.

        CRITICAL FIX: Deserialize JSON strings in metadata back to Python types.

        Before: metadata values containing dicts were JSON strings
        After: metadata values are properly deserialized to native Python types

        Args:
            entity_id: Session identifier

        Returns:
            Session data with metadata (with JSON values deserialized), or None if not found
        """
        try:
            with self._open_file("r") as f:
                if entity_id not in f[self.SESSIONS_GROUP]:  # type: ignore[operator]
                    return None

                session_group = f[self.SESSIONS_GROUP][entity_id]  # type: ignore[index]
                raw_metadata = dict(session_group.attrs)  # type: ignore[attr-defined]

                # CRITICAL: Deserialize JSON strings back to Python types (DRY)
                metadata = self._deserialize_metadata(raw_metadata)

                return {
                    "session_id": entity_id,
                    "metadata": metadata,
                    "status": metadata.get("status", "unknown"),
                }

        except Exception as e:
            logger.error("SESSION_READ_FAILED", session_id=entity_id, error=str(e))
            return None

    def update(
        self,
        entity_id: str,
        entity: dict[str, Optional[Any]],
    ) -> bool:
        """Update session status and metadata.

        Args:
            entity_id: Session identifier
            entity: Dict with 'status', 'metadata' keys

        Returns:
            True if update successful
        """
        session_id = entity_id
        status = entity.get("status")
        metadata = entity.get("metadata")
        try:
            with self._open_file("r+") as f:
                if session_id not in f[self.SESSIONS_GROUP]:  # type: ignore[operator]
                    return False

                session_group = f[self.SESSIONS_GROUP][session_id]  # type: ignore[index]

                if status:
                    session_group.attrs["status"] = status  # type: ignore[attr-defined]

                # DRY: Use _serialize_metadata helper (same as create())
                if metadata:
                    serialized_metadata = self._serialize_metadata(metadata)
                    for key, value in serialized_metadata.items():
                        session_group.attrs[key] = value  # type: ignore[attr-defined]

                session_group.attrs["updated_at"] = datetime.now(timezone.utc).isoformat()  # type: ignore[attr-defined]

            self._log_operation("update", session_id)
            return True

        except Exception as e:
            self._log_operation("update", session_id, status="failed", error=str(e))
            return False

    def delete(self, entity_id: str) -> bool:
        """Delete session (marks as deleted).

        Args:
            entity_id: Session identifier

        Returns:
            True if deletion successful
        """
        session_id = entity_id
        try:
            with self._open_file("r+") as f:
                if session_id not in f[self.SESSIONS_GROUP]:  # type: ignore[operator]
                    return False

                session_group = f[self.SESSIONS_GROUP][session_id]  # type: ignore[index]
                session_group.attrs["status"] = "deleted"  # type: ignore[attr-defined]
                session_group.attrs["deleted_at"] = datetime.now(timezone.utc).isoformat()  # type: ignore[attr-defined]

            self._log_operation("delete", session_id)
            return True

        except Exception as e:
            self._log_operation("delete", session_id, status="failed", error=str(e))
            return False

    def list_all(
        self, limit: Optional[int] = None, status: Optional[str] = None
    ) -> list[dict[str, Any]]:
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
                session_ids = list(sessions_group.keys())  # type: ignore[attr-defined]

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
