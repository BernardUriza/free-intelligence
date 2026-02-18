"""Session Service - Business logic for medical sessions.

Handles session lifecycle:
- Session creation
- Status tracking (all task types)
- Session finalization
- Task aggregation

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-12-18 (refactored with DI)
Card: Clean Architecture Refactor
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models.task_type import TaskStatus, TaskType
from backend.infrastructure.interfaces.ievent_bus import IEventBus
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.repositories.interfaces import ITaskRepository


class SessionService:
    """Service for medical session management.

    Provides unified view of session state across all task types.
    """

    def __init__(self, logger: ILogger, task_repository: ITaskRepository, event_bus: IEventBus):
        """Initialize SessionService with dependencies.

        Args:
            logger: Logger instance
            task_repository: Task repository instance
            event_bus: Event bus instance
        """
        self.logger = logger
        self.task_repository = task_repository
        self.event_bus = event_bus

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
            if self.task_repository.task_exists(session_id, task_type):
                meta = self.task_repository.get_task_metadata(session_id, task_type) or {}
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
        now = datetime.now(timezone.utc)
        created_at = earliest_created.isoformat() if earliest_created else now.isoformat()
        updated_at = latest_updated.isoformat() if latest_updated else now.isoformat()

        self.logger.info(
            "SESSION_INFO_RETRIEVED", session_id=session_id, task_count=len(tasks_metadata)
        )

        # Publish event for decoupled communication
        self.event_bus.publish(
            "session.info_retrieved",
            {
                "session_id": session_id,
                "overall_status": overall_status,
                "task_count": len(tasks_metadata),
                "timestamp": updated_at,
            },
        )

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
            return TaskStatus.PENDING.name.lower()

        statuses = [
            meta.get("status", TaskStatus.PENDING.name.lower()) for meta in tasks_metadata.values()
        ]

        # Priority: FAILED > IN_PROGRESS > COMPLETED > PENDING
        if TaskStatus.FAILED.name.lower() in statuses:
            return TaskStatus.FAILED.name.lower()

        if TaskStatus.IN_PROGRESS.name.lower() in statuses:
            return TaskStatus.IN_PROGRESS.name.lower()

        if all(s == TaskStatus.COMPLETED.name.lower() for s in statuses):
            return TaskStatus.COMPLETED.name.lower()

        return TaskStatus.PENDING.name.lower()
