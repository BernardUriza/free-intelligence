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

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.storage.task_repository import get_task_metadata, task_exists

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
        """Get complete session information (all tasks).

        Aggregates status from all task types:
        - TRANSCRIPTION: Audio → text conversion
        - DIARIZATION: Speaker identification + text improvement
        - SOAP_GENERATION: Medical notes extraction
        - EMOTION_ANALYSIS: Patient emotion detection
        - ENCRYPTION: AES-GCM audio encryption

        Args:
            session_id: Session UUID

        Returns:
            dict with:
                - session_id: Session identifier
                - created_at: Earliest task creation timestamp
                - updated_at: Latest task update timestamp
                - overall_status: Overall session status
                - tasks: Dict of {task_type: metadata} for all present tasks
                - task_count: Number of tasks in session

        Raises:
            ValueError: If session not found (no tasks exist)
        """
        # Collect all task metadata
        tasks_metadata: dict[str, dict] = {}
        earliest_created: datetime | None = None
        latest_updated: datetime | None = None

        for task_type in TaskType:
            if task_exists(session_id, task_type):
                meta = get_task_metadata(session_id, task_type) or {}
                tasks_metadata[task_type.value] = meta

                # Track timestamps
                if "created_at" in meta:
                    try:
                        created_dt = datetime.fromisoformat(meta["created_at"])
                        if earliest_created is None or created_dt < earliest_created:
                            earliest_created = created_dt
                    except (ValueError, TypeError):
                        pass

                if "updated_at" in meta:
                    try:
                        updated_dt = datetime.fromisoformat(meta["updated_at"])
                        if latest_updated is None or updated_dt > latest_updated:
                            latest_updated = updated_dt
                    except (ValueError, TypeError):
                        pass

        # Session must have at least one task
        if not tasks_metadata:
            raise ValueError(f"Session {session_id} not found")

        # Determine overall status
        overall_status = self._compute_overall_status(tasks_metadata)

        # Use timestamps or defaults
        now = datetime.now(UTC)
        created_at = earliest_created.isoformat() if earliest_created else now.isoformat()
        updated_at = latest_updated.isoformat() if latest_updated else now.isoformat()

        return {
            "session_id": session_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "overall_status": overall_status,
            "tasks": tasks_metadata,
            "task_count": len(tasks_metadata),
        }

    def _compute_overall_status(self, tasks_metadata: dict[str, dict]) -> str:
        """Compute overall session status from task metadata.

        Rules:
        - If ANY task is FAILED → overall = FAILED
        - If ALL tasks are COMPLETED → overall = COMPLETED
        - If ANY task is IN_PROGRESS → overall = IN_PROGRESS
        - Otherwise → overall = PENDING

        Args:
            tasks_metadata: Dict of {task_type: metadata}

        Returns:
            Overall status string
        """
        if not tasks_metadata:
            return TaskStatus.PENDING.value

        statuses = [
            meta.get("status", TaskStatus.PENDING.value) for meta in tasks_metadata.values()
        ]

        # Priority: FAILED > IN_PROGRESS > COMPLETED > PENDING
        if TaskStatus.FAILED.value in statuses:
            return TaskStatus.FAILED.value

        if TaskStatus.IN_PROGRESS.value in statuses:
            return TaskStatus.IN_PROGRESS.value

        if all(s == TaskStatus.COMPLETED.value for s in statuses):
            return TaskStatus.COMPLETED.value

        return TaskStatus.PENDING.value
