"""Workflow orchestrator interface for dependency inversion.

This interface abstracts the dispatch mechanism for workflow tasks,
decoupling business logic from executor implementations (ThreadPoolExecutor vs Celery).
"""

from abc import ABC, abstractmethod
from typing import Any


class IWorkflowOrchestrator(ABC):
    """
    Interface for workflow task dispatch and orchestration.

    Responsibilities:
    - Dispatch async tasks to workers (diarization, SOAP, encryption, etc.)
    - Track task status and metadata
    - Handle task failures and retries

    Decouples:
    - API layer from worker execution infrastructure
    - Business logic from ThreadPoolExecutor/Celery implementation details

    Clean Architecture Benefits:
    - Business logic depends on interface, not concrete executor
    - Easy to swap ThreadPoolExecutor → Celery without changing callers
    - Testable via mocks (no real workers needed)
    """

    @abstractmethod
    async def dispatch_diarization(
        self,
        session_id: str,
        audio_file_path: str,
        language: str = "es",
    ) -> dict[str, Any]:
        """
        Dispatch speaker diarization task for audio.

        Args:
            session_id: Unique session identifier
            audio_file_path: Path to audio file (e.g., storage/{session_id}/audio.webm)
            language: Audio language code (default: "es" for Spanish)

        Returns:
            dict with keys:
            - task_id: Unique task identifier
            - status: "dispatched" | "pending" | "failed"
            - estimated_duration_seconds: Expected completion time
            - error: Optional error message if dispatch failed

        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If session_id or language invalid
        """
        ...

    @abstractmethod
    async def dispatch_soap_generation(
        self,
        session_id: str,
        language: str = "es",
    ) -> dict[str, Any]:
        """
        Dispatch SOAP note generation task.

        Requires:
        - Transcription must be completed first
        - Session must have transcript data

        Args:
            session_id: Unique session identifier
            language: Note language code (default: "es")

        Returns:
            dict with keys:
            - task_id: Unique task identifier
            - status: "dispatched" | "pending" | "blocked"
            - blocked_by: List of task types that must complete first
            - estimated_duration_seconds: Expected completion time

        Raises:
            ValueError: If session has no transcript data
        """
        ...

    @abstractmethod
    async def dispatch_emotion_analysis(
        self,
        session_id: str,
        language: str = "es",
    ) -> dict[str, Any]:
        """
        Dispatch emotional analysis task.

        Analyzes patient emotional state from conversation transcript
        using Ollama Llama 3.1 8B with fallback to heuristics.

        Args:
            session_id: Unique session identifier
            language: Analysis language code (default: "es")

        Returns:
            dict with keys:
            - task_id: Unique task identifier
            - status: "dispatched" | "pending"
            - model_used: "llama3.1:8b" | "heuristic"
            - estimated_duration_seconds: Expected completion time

        Raises:
            ValueError: If session has no transcript data
        """
        ...

    @abstractmethod
    async def dispatch_encryption(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Dispatch data encryption task for session.

        Encrypts sensitive session data (audio, transcript, SOAP note)
        for compliance (HIPAA, GDPR).

        Args:
            session_id: Unique session identifier

        Returns:
            dict with keys:
            - task_id: Unique task identifier
            - status: "dispatched" | "pending"
            - encrypted_artifacts: List of artifact types encrypted

        Raises:
            ValueError: If session has no artifacts to encrypt
        """
        ...

    @abstractmethod
    async def dispatch_workflow(
        self,
        session_id: str,
        workflow_type: str,
        language: str = "es",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generic workflow dispatch (supports any workflow type).

        Args:
            session_id: Unique session identifier
            workflow_type: One of: "diarization", "transcription", "soap_generation",
                           "emotion_analysis", "encryption"
            language: Language code (default: "es")
            **kwargs: Additional workflow-specific parameters

        Returns:
            dict with task metadata (same structure as specific dispatch methods)

        Raises:
            ValueError: If workflow_type is unknown
        """
        ...
