"""Intelligent orchestration service implementation.

This service extracts the complex business logic from the workflows endpoint,
enabling thin controllers and testable orchestration.
"""

from typing import Any

from backend.infrastructure.interfaces.ilogger import ILogger
from backend.models.task_type import TaskStatus, TaskType
from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.services.workflow.constants import (
    AUDIO_BITRATE_BYTES_PER_SECOND,
    DEFAULT_AUDIO_DURATION_SECONDS,
    WORKFLOW_DIARIZATION,
    WORKFLOW_EMOTION,
    WORKFLOW_SOAP,
    WORKFLOW_TRANSCRIPTION,
)
from backend.services.workflow.interfaces import (
    IIntelligentOrchestrationService,
    IWorkflowOrchestrator,
    IWorkflowRouter,
    IWorkflowTracker,
)


class IntelligentOrchestrationService(IIntelligentOrchestrationService):
    """
    Service for intelligent workflow orchestration (business logic layer).

    Responsibilities:
    1. Detect audio metadata (duration, format)
    2. Query existing tasks to avoid duplicates
    3. Route workflows using intelligent router
    4. Dispatch workflows in optimal order
    5. Track workflow progress
    6. Return unified response

    Dependencies (constructor injection):
    - orchestrator: Dispatches tasks to workers
    - router: Decides which workflows to execute
    - tracker: Tracks workflow state (thread-safe)
    - task_repository: Queries task metadata
    - corpus_repository: Queries audio/session data
    - logger: Structured logging
    """

    def __init__(
        self,
        orchestrator: IWorkflowOrchestrator,
        router: IWorkflowRouter,
        tracker: IWorkflowTracker,
        task_repository: ITaskRepository,
        corpus_repository: ICorpusRepository,
        logger: ILogger,
    ):
        """Initialize service with dependencies (constructor injection)."""
        self.orchestrator = orchestrator
        self.router = router
        self.tracker = tracker
        self.task_repo = task_repository
        self.corpus_repo = corpus_repository
        self.logger = logger

    async def orchestrate_intelligent_workflow(
        self,
        session_id: str,
        audio_file_path: str,
        language: str = "es",
        user_intent: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrate intelligent workflow execution for a session.

        Algorithm:
        1. Detect audio duration from file metadata (fallback to estimate)
        2. Query existing tasks to avoid duplicates
        3. Route workflows using intelligent router
        4. Dispatch workflows in optimal order
        5. Track workflow progress
        6. Return unified response with task IDs and metadata

        Args:
            session_id: Unique session identifier
            audio_file_path: Path to audio file (e.g., storage/{session_id}/audio.webm)
            language: Session language code (default: "es")
            user_intent: Optional user-provided intent

        Returns:
            dict with orchestration results (workflows dispatched, task IDs, status)

        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If session_id or language invalid
        """
        self.logger.info(
            "INTELLIGENT_WORKFLOW_STARTED",
            session_id=session_id,
            audio_file_path=audio_file_path,
            language=language,
            user_intent=user_intent,
        )

        # Step 1: Detect audio duration
        audio_duration_seconds = await self._detect_audio_duration(session_id, audio_file_path)

        # Step 2: Get existing tasks to avoid duplicates
        existing_tasks = await self._get_existing_task_types(session_id)

        # Step 3: Route workflows using intelligent router
        decision = self.router.route_workflows(
            session_id=session_id,
            audio_duration_seconds=audio_duration_seconds,
            language=language,
            existing_tasks=existing_tasks,
            user_intent=user_intent,
        )

        # Extract RoutingCost object for cleaner access
        routing_cost = decision["cost"]

        self.logger.info(
            "WORKFLOW_ROUTING_DECISION",
            session_id=session_id,
            workflows=decision["workflows"],
            reasoning=decision["reasoning"],
            cost_usd=routing_cost.routing_cost_usd,
            savings_usd=routing_cost.execution_cost_saved_usd,
        )

        # Step 4: Dispatch workflows in optimal order
        task_ids = await self._dispatch_workflows(
            session_id=session_id,
            workflows=decision["workflows"],
            language=language,
        )

        # Step 5: Build unified response
        workflows_dispatched = [w for w in decision["workflows"] if w != WORKFLOW_TRANSCRIPTION]
        skipped_workflows = [w for w in decision["workflows"] if w == WORKFLOW_TRANSCRIPTION]

        return {
            "session_id": session_id,
            "status": "dispatched",
            "workflows_dispatched": workflows_dispatched,
            "task_ids": task_ids,
            "routing_decision": {
                "workflows": decision["workflows"],
                "reasoning": decision["reasoning"],
                "parallel_execution": decision.get("parallel", True),
                "estimated_cost_usd": routing_cost.routing_cost_usd,
                "estimated_duration_seconds": decision.get("estimated_duration_seconds", 0),
            },
            "audio_duration_seconds": audio_duration_seconds,
            "existing_tasks_skipped": skipped_workflows,
            "cost": {
                "routing_usd": routing_cost.routing_cost_usd,
                "tokens_saved": routing_cost.execution_tokens_saved,
                "savings_usd": routing_cost.execution_cost_saved_usd,
                "net_savings_usd": (
                    routing_cost.execution_cost_saved_usd - routing_cost.routing_cost_usd
                ),
            },
            "message": (
                f"Intelligent orchestration complete: {len(workflows_dispatched)} workflows dispatched. "
                f"Poll /sessions/{session_id}/monitor for progress."
            ),
        }

    async def _detect_audio_duration(
        self,
        session_id: str,
        audio_file_path: str,
    ) -> float:
        """
        Detect audio duration from file metadata.

        Strategy:
        1. Try to get audio bytes from corpus repository
        2. Estimate duration: bytes / AUDIO_BITRATE_BYTES_PER_SECOND
        3. Fallback to DEFAULT_AUDIO_DURATION_SECONDS if detection fails

        Args:
            session_id: Unique session identifier
            audio_file_path: Path to audio file

        Returns:
            Audio duration in seconds (detected or fallback)
        """
        try:
            # Try to get audio bytes from corpus repository
            audio_bytes_data = self.corpus_repo.get_session_audio(
                session_id, "tasks/TRANSCRIPTION/full_audio.webm"
            )

            if audio_bytes_data:
                # Estimate duration from file size
                # Formula: duration_seconds = bytes / (bitrate_bytes_per_second)
                audio_duration_seconds = len(audio_bytes_data) / AUDIO_BITRATE_BYTES_PER_SECOND

                self.logger.info(
                    "AUDIO_DURATION_DETECTED",
                    session_id=session_id,
                    duration_seconds=audio_duration_seconds,
                    file_size_bytes=len(audio_bytes_data),
                )

                return audio_duration_seconds
            else:
                # No audio data found, use fallback
                self.logger.warning(
                    "AUDIO_DURATION_DETECTION_FAILED",
                    session_id=session_id,
                    error="No audio data found",
                    hint=f"Using default duration of {DEFAULT_AUDIO_DURATION_SECONDS}s",
                )
                return DEFAULT_AUDIO_DURATION_SECONDS

        except Exception as e:
            # Detection failed, use fallback
            self.logger.warning(
                "AUDIO_DURATION_DETECTION_FAILED",
                session_id=session_id,
                error=str(e),
                hint=f"Using default duration of {DEFAULT_AUDIO_DURATION_SECONDS}s",
            )
            return DEFAULT_AUDIO_DURATION_SECONDS

    async def _get_existing_task_types(self, session_id: str) -> list[str]:
        """
        Query existing completed tasks to avoid duplicates.

        Strategy:
        1. List all task types for session
        2. For each task, get metadata
        3. Check if status is "completed"
        4. Return list of completed task type names

        Args:
            session_id: Unique session identifier

        Returns:
            List of completed task type names (e.g., ["transcription", "diarization"])
        """
        existing_tasks: list[str] = []

        try:
            task_types = self.corpus_repo.list_session_tasks(session_id)

            for task_type in task_types:
                try:
                    # Construct TaskType enum
                    constructed_task = TaskType(task_type)

                    # Get task metadata
                    metadata = self.task_repo.get_task_metadata(session_id, constructed_task)

                    if not metadata:
                        continue

                    # Check if task is completed
                    status_val = metadata.get("status")
                    is_completed = (
                        status_val == "completed"
                        or status_val == TaskStatus.COMPLETED.name.lower()
                        or status_val == TaskStatus.COMPLETED
                    )

                    if is_completed:
                        existing_tasks.append(task_type)

                except (ValueError, KeyError) as e:
                    # Invalid task type or missing metadata, skip
                    self.logger.debug(
                        "TASK_TYPE_SKIP",
                        session_id=session_id,
                        task_type=task_type,
                        error=str(e),
                    )
                    continue

        except Exception as e:
            # Query failed, assume no existing tasks
            self.logger.warning(
                "EXISTING_TASKS_DETECTION_FAILED",
                session_id=session_id,
                error=str(e),
            )

        return existing_tasks

    async def _dispatch_workflows(
        self,
        session_id: str,
        workflows: list[str],
        language: str,
    ) -> dict[str, str]:
        """
        Dispatch workflows to workers in optimal order.

        Strategy:
        1. For each workflow in decision:
           a. Ensure task exists in repository
           b. Skip transcription (handled during upload)
           c. Dispatch diarization, SOAP, emotion analysis
        2. Return dict mapping workflow_type → task_id

        Args:
            session_id: Unique session identifier
            workflows: List of workflow types to dispatch
            language: Session language code

        Returns:
            dict mapping workflow_type → task_id (e.g., {"diarization": "task-123"})
        """
        task_ids: dict[str, str] = {}

        for workflow in workflows:
            try:
                # Ensure task exists in repository (idempotent)
                task_type = TaskType(workflow)
                self.task_repo.ensure_task_exists(
                    session_id=session_id,
                    task_type=task_type.value,
                )

                # Skip transcription (handled during upload)
                if task_type == TaskType.TRANSCRIPTION:
                    self.logger.info(
                        "TRANSCRIPTION_SKIPPED",
                        session_id=session_id,
                        hint="Transcription handled during upload",
                    )
                    continue

                # Dispatch workflow using orchestrator (methods only accept session_id)
                if task_type == TaskType.DIARIZATION:
                    result = await self.orchestrator.dispatch_diarization(session_id=session_id)
                    task_ids[WORKFLOW_DIARIZATION] = result.get("task_id", session_id)

                elif task_type == TaskType.SOAP_GENERATION:
                    result = await self.orchestrator.dispatch_soap_generation(session_id=session_id)
                    task_ids[WORKFLOW_SOAP] = result.get("task_id", session_id)

                elif task_type == TaskType.EMOTION_ANALYSIS:
                    result = await self.orchestrator.dispatch_emotion_analysis(session_id=session_id)
                    task_ids[WORKFLOW_EMOTION] = result.get("task_id", session_id)

                self.logger.info(
                    "WORKFLOW_DISPATCHED",
                    session_id=session_id,
                    task_type=workflow,
                    task_id=task_ids.get(workflow, "unknown"),
                )

            except Exception as e:
                self.logger.error(
                    "WORKFLOW_DISPATCH_FAILED",
                    session_id=session_id,
                    workflow=workflow,
                    error=str(e),
                    exc_info=True,
                )
                # Continue dispatching other workflows (partial success)
                continue

        return task_ids
