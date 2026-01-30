"""Chunk Handler Abstraction - Strategy Pattern for audio chunk processing.

Philosophy:
  Separates WHAT (transcribe audio) from WHERE (storage strategy).

  WHAT = Shared logic (STT load balancer, validation, error handling)
  WHERE = Strategy-specific (HDF5 persistent vs in-memory ephemeral)

Architecture:
  - ChunkHandler (ABC) - Interface defining chunk lifecycle
  - MedicalChunkHandler - HDF5 persistent storage + post-processing
  - ChatChunkHandler - In-memory ephemeral storage (no post-processing)

Usage:
  handler = get_chunk_handler(mode)  # Factory
  await handler.initialize_session(session_id)
  await handler.save_chunk(session_id, chunk_number, audio_bytes, transcript, metadata)
  status = await handler.get_session_status(session_id)
  await handler.finalize_session(session_id)

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: Voice chat integration (refactored backend)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ChunkHandler(ABC):
    """Abstract handler for audio chunk processing.

    Defines the contract for chunk lifecycle:
    1. initialize_session() - Setup or clear session
    2. save_chunk() - Store chunk + transcription
    3. get_session_status() - Poll status
    4. finalize_session() - Cleanup or post-processing

    Implementations:
    - MedicalChunkHandler: HDF5 persistent storage
    - ChatChunkHandler: In-memory ephemeral storage
    """

    @abstractmethod
    async def initialize_session(
        self,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize or clear session.

        Called on first chunk (chunk_number == 0).

        Args:
            session_id: Session identifier
            metadata: Optional session metadata (patient info for medical, user info for chat)

        Medical behavior:
            - Create HDF5 task structure (/sessions/{id}/tasks/TRANSCRIPTION/)
            - Save patient metadata to session attributes

        Chat behavior:
            - Clear previous chat session for this user
            - Reset in-memory chunk list
        """
        pass

    @abstractmethod
    async def save_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_bytes: bytes,
        transcript: str,
        metadata: dict[str, Any],
    ) -> None:
        """Save chunk with transcription.

        Called after successful STT transcription.

        Args:
            session_id: Session identifier
            chunk_number: Chunk index (0, 1, 2, ...)
            audio_bytes: Raw audio data (WebM/WAV/MP3)
            transcript: Transcription text from STT
            metadata: Provider, confidence, timestamp, duration, etc.

        Medical behavior:
            - Save audio_bytes to HDF5 chunk dataset
            - Save transcript + metadata to HDF5 chunk metadata

        Chat behavior:
            - Save transcript + metadata to in-memory dict
            - Discard audio_bytes (ephemeral, no persistence)
        """
        pass

    @abstractmethod
    async def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Get session status for polling.

        Called by GET /jobs/{session_id} endpoint.

        Args:
            session_id: Session identifier

        Returns:
            dict with keys:
                - session_id: str
                - status: str (pending | in_progress | completed | failed)
                - total_chunks: int
                - processed_chunks: int
                - progress_percent: int (0-100)
                - chunks: list[dict] (chunk metadata)

        Medical behavior:
            - Read from HDF5 session chunks
            - Calculate progress from chunk statuses

        Chat behavior:
            - Read from in-memory dict
            - All chunks immediately completed (no workers)
        """
        pass

    @abstractmethod
    async def finalize_session(self, session_id: str) -> dict[str, Any]:
        """Finalize session (cleanup or post-processing).

        Called by POST /end-session endpoint (medical) or chat stop (chat).

        Args:
            session_id: Session identifier

        Returns:
            dict with finalization result

        Medical behavior:
            - Trigger diarization worker
            - Return job_id for diarization polling

        Chat behavior:
            - No-op (ephemeral, no post-processing)
            - Return success status
        """
        pass
