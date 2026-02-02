"""Checkpoint service - Stub for incomplete Clean Architecture refactor.

STATUS: NOT IMPLEMENTED
The Clean Architecture refactor was started but never completed.
- checkpoint_use_case.py exists but imports non-existent modules (domain, ports)
- The endpoint at /sessions/{session_id}/checkpoint is registered but broken

This file provides stub classes so imports don't fail at startup.
The endpoint will raise NotImplementedError if called.

TODO(Phase 5): Complete Clean Architecture refactor or revert to simple implementation:
1. Create domain entities (AudioChunk, AudioFormat, CheckpointRange, CheckpointResult, SessionId)
2. Create ports (AudioRepositoryPort, AudioConcatenatorPort)
3. Implement adapters for HDF5 repository
4. Create factory function with proper DI

Author: Bernard Uriza Orozco
Updated: 2026-02-02 (Stub for broken imports)
"""

from __future__ import annotations

from dataclasses import dataclass


class CheckpointError(Exception):
    """Base exception for checkpoint use case errors."""

    pass


class NoChunksToProcessError(CheckpointError):
    """Raised when no chunks are available in the checkpoint range."""

    pass


class TooManyChunksError(CheckpointError):
    """Raised when chunk count exceeds safety limit."""

    pass


@dataclass(frozen=True, slots=True)
class CheckpointRequest:
    """Input DTO for checkpoint creation.

    Stub implementation - real validation in checkpoint_use_case.py
    """

    session_id: str
    last_checkpoint_idx: int
    new_checkpoint_idx: int

    def __post_init__(self) -> None:
        """Validate request parameters."""
        if not self.session_id or len(self.session_id) < 5:
            raise ValueError("session_id must be at least 5 characters")
        if self.last_checkpoint_idx < -1:
            raise ValueError("last_checkpoint_idx must be >= -1")
        if self.new_checkpoint_idx < 0:
            raise ValueError("new_checkpoint_idx must be >= 0")
        if self.new_checkpoint_idx <= self.last_checkpoint_idx:
            raise ValueError("new_checkpoint_idx must be > last_checkpoint_idx")


@dataclass
class CheckpointResult:
    """Result of checkpoint creation - stub."""

    chunks_concatenated: int
    audio_bytes: bytes


class CheckpointService:
    """Stub checkpoint service that raises NotImplementedError."""

    def execute(self, request: CheckpointRequest) -> CheckpointResult:  # noqa: ARG002
        """Execute checkpoint - NOT IMPLEMENTED."""
        raise NotImplementedError(
            "Checkpoint service not implemented. "
            "Clean Architecture refactor incomplete. "
            "See TODO in backend/infrastructure/common/services/checkpoint.py"
        )


def create_checkpoint_service() -> CheckpointService:
    """Factory function for checkpoint service.

    Returns a stub service that raises NotImplementedError.
    This allows the endpoint to compile but fail gracefully at runtime.
    """
    return CheckpointService()
