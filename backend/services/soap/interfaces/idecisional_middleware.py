"""Interface for DecisionalMiddleware - enables dependency injection.

This interface defines the contract for intelligent SOAP orchestration.
Workers depend on this interface, not the concrete DecisionalMiddleware implementation.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Eliminate Service Locator
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.services.soap.services.decisional_middleware import OrchestrationResult


class IDecisionalMiddleware(ABC):
    """Abstract interface for SOAP generation orchestration.

    The DecisionalMiddleware analyzes transcript complexity and decides
    the optimal SOAP generation strategy (SIMPLE, MODERATE, COMPLEX, CRITICAL).

    Used by:
        - soap_worker: orchestrates SOAP note generation
    """

    @abstractmethod
    def process(
        self,
        transcript: str,
        segments: list[dict[str, Any]] | None = None,
        session_metadata: dict[str, Any] | None = None,
    ) -> "OrchestrationResult":
        """Process a transcript and generate SOAP note.

        This is the main orchestration method that:
        1. Analyzes transcript complexity
        2. Plans orchestration strategy
        3. Executes multi-persona generation
        4. Returns result with metadata

        Args:
            transcript: Full medical conversation text
            segments: Optional diarization segments (speaker-labeled)
            session_metadata: Optional session context (session_id, provider, etc)

        Returns:
            OrchestrationResult with:
            - soap_note: The generated SOAP note dict
            - strategy_used: SIMPLE, MODERATE, COMPLEX, or CRITICAL
            - personas_invoked: List of personas used
            - confidence_score: 0-1 confidence metric
            - doctor_context_requested: Whether more context is needed
        """
        pass
