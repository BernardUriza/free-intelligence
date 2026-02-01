"""Workflow routing interface for intelligent workflow decisions.

This interface abstracts routing logic, enabling rule-based or LLM-based decisions
without changing orchestration code.
"""

from abc import ABC, abstractmethod
from typing import Any


class IWorkflowRouter(ABC):
    """
    Interface for workflow routing decisions.

    Responsibilities:
    - Decide which workflows to execute for a session
    - Determine execution order (parallel vs sequential)
    - Estimate cost and duration
    - Provide reasoning for decisions (explainability)

    Decouples:
    - Orchestration logic from routing strategy
    - Business logic from implementation (rule-based vs LLM-based)

    Clean Architecture Benefits:
    - Easy to swap rule-based → LLM-based routing without changing callers
    - Testable via mocks (no real LLM calls needed)
    - Explainable AI (reasoning field explains decisions)

    Implementation Options:
    - Rule-based: Deterministic logic (audio duration, existing tasks)
    - LLM-based: GPT-4 decides workflows based on user intent
    - Hybrid: Rules for common cases, LLM for edge cases
    """

    @abstractmethod
    def route_workflows(
        self,
        session_id: str,
        audio_duration_seconds: float,
        language: str = "es",
        existing_tasks: list[str] | None = None,
        user_intent: str | None = None,
    ) -> dict[str, Any]:
        """
        Decide which workflows to execute for a session.

        Decision Factors:
        - Audio duration: >60s requires diarization, <60s can skip
        - Existing tasks: Don't re-run completed workflows
        - User intent: "quick note" → skip diarization, "detailed analysis" → all workflows

        Args:
            session_id: Unique session identifier
            audio_duration_seconds: Duration of audio recording
            language: Session language code
            existing_tasks: List of already-completed task types
                           (e.g., ["transcription", "diarization"])
            user_intent: Optional user-provided intent
                        (e.g., "quick consult", "detailed follow-up")

        Returns:
            dict with keys:
            - workflows: List of workflow types to execute
                        (e.g., ["diarization", "transcription", "soap_generation"])
            - reasoning: Human-readable explanation of decision
                        (e.g., "Audio >60s requires diarization for speaker attribution")
            - parallel_execution: True if workflows can run in parallel, False if sequential
            - estimated_cost_usd: Total estimated cost (LLM calls, compute)
            - estimated_duration_seconds: Total estimated time to completion

        Example Return:
            {
                "workflows": ["diarization", "transcription", "soap_generation"],
                "reasoning": "Audio duration 3m45s requires diarization. "
                             "User intent 'detailed analysis' includes SOAP note.",
                "parallel_execution": True,
                "estimated_cost_usd": 0.05,
                "estimated_duration_seconds": 120,
            }

        Raises:
            ValueError: If audio_duration_seconds is negative or zero
        """
        ...
