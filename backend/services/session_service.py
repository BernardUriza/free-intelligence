"""Session Service - Business logic for medical sessions.

Handles session lifecycle:
- Session creation
- Status tracking
- Session finalization

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Clean Architecture Refactor
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import get_task_metadata, task_exists

logger = get_logger(__name__)


class SessionService:
    """Service for medical session management."""

    async def get_session_info(self, session_id: str) -> dict:
        """Get complete session information.

        Args:
            session_id: Session UUID

        Returns:
            dict with session metadata and task status

        Raises:
            ValueError: If session not found
        """
        # Check if any task exists for this session
        has_transcription = task_exists(session_id, TaskType.TRANSCRIPTION)

        if not has_transcription:
            raise ValueError(f"Session {session_id} not found")

        # Get transcription metadata
        transcription_meta = get_task_metadata(session_id, TaskType.TRANSCRIPTION) or {}

        return {
            "session_id": session_id,
            "created_at": transcription_meta.get("created_at", datetime.now(UTC).isoformat()),
            "updated_at": transcription_meta.get("updated_at", datetime.now(UTC).isoformat()),
            "has_transcription": has_transcription,
            "transcription_status": transcription_meta.get("status", "unknown"),
        }
