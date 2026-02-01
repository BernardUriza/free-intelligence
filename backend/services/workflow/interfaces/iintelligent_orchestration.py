"""Intelligent orchestration service interface for high-level business logic.

This interface abstracts the complex orchestration logic (audio detection, routing,
dispatch) into a single service, enabling thin controllers.
"""

from abc import ABC, abstractmethod
from typing import Any


class IIntelligentOrchestrationService(ABC):
    """
    Interface for intelligent workflow orchestration (high-level business logic).

    Responsibilities:
    - Detect audio metadata (duration, format)
    - Query existing tasks to avoid duplicates
    - Route workflows based on intelligent decisions
    - Dispatch workflows in optimal order (parallel vs sequential)
    - Track workflow progress
    - Return unified response to controllers

    Decouples:
    - Controllers from business logic (thin controllers)
    - HTTP layer from orchestration complexity
    - API design from implementation details

    Clean Architecture Benefits:
    - Controllers become 10-20 lines (no business logic)
    - Business logic testable without HTTP layer
    - Easy to add new workflows without changing controllers

    Usage Pattern:
        # Controller (thin, 15 lines):
        @router.post("/sessions/{session_id}/analyze")
        async def analyze_session(
            session_id: str,
            orchestration_service: IntelligentOrchestrationDep,
        ) -> dict:
            result = await orchestration_service.orchestrate_intelligent_workflow(
                session_id=session_id,
                audio_file_path=f"storage/{session_id}/audio.webm",
                language="es",
            )
            return result

        # Business logic (service layer, 200+ lines):
        class IntelligentOrchestrationService(IIntelligentOrchestrationService):
            async def orchestrate_intelligent_workflow(...):
                # 1. Detect audio duration
                # 2. Query existing tasks
                # 3. Route workflows
                # 4. Dispatch workflows
                # 5. Track progress
                # 6. Return unified response
    """

    @abstractmethod
    async def orchestrate_intelligent_workflow(
        self,
        session_id: str,
        audio_file_path: str,
        language: str = "es",
        user_intent: str | None = None,
    ) -> dict[str, Any]:
        """
        Orchestrate intelligent workflow execution for a session.

        High-level algorithm:
        1. Detect audio duration from file metadata (fallback to estimate)
        2. Query existing tasks to avoid duplicates
        3. Route workflows using intelligent router (rule-based or LLM)
        4. Dispatch workflows in optimal order (parallel if possible)
        5. Track workflow progress
        6. Return unified response with task IDs and metadata

        Args:
            session_id: Unique session identifier
            audio_file_path: Path to audio file (e.g., storage/{session_id}/audio.webm)
            language: Session language code (default: "es")
            user_intent: Optional user-provided intent
                        (e.g., "quick consult", "detailed follow-up")

        Returns:
            dict with keys:
            - session_id: Session identifier
            - workflows_dispatched: List of dispatched workflow types
                                   (e.g., ["diarization", "soap_generation"])
            - task_ids: Dict[workflow_type, task_id] mapping
            - routing_decision: Router's decision metadata
                               (workflows, reasoning, estimated_cost, estimated_duration)
            - audio_duration_seconds: Detected audio duration
            - existing_tasks_skipped: List of workflows skipped (already completed)
            - status: "dispatched" | "partially_dispatched" | "failed"
            - error: Optional error message if dispatch failed

        Example Return:
            {
                "session_id": "session-123",
                "workflows_dispatched": ["diarization", "soap_generation"],
                "task_ids": {
                    "diarization": "task-456",
                    "soap_generation": "task-789",
                },
                "routing_decision": {
                    "workflows": ["diarization", "transcription", "soap_generation"],
                    "reasoning": "Audio >60s requires diarization...",
                    "estimated_cost_usd": 0.05,
                    "estimated_duration_seconds": 120,
                },
                "audio_duration_seconds": 225.3,
                "existing_tasks_skipped": ["transcription"],
                "status": "dispatched",
            }

        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If session_id or language invalid
            WorkflowRoutingError: If routing logic fails
            WorkflowDispatchError: If dispatch to workers fails
        """
        ...
