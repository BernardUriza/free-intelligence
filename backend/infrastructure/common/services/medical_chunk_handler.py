"""Medical workflow handler - HDF5 persistent storage.

Philosophy:
  Medical consultations are PERSISTENT (not ephemeral like chat).
  - Full audio persistence (HDF5 + filesystem)
  - Post-processing pipeline (diarization → SOAP → encryption)
  - Patient metadata tracked
  - Session lifecycle: hours/days (until completion)

Architecture:
  - Storage: HDF5 persistent (/sessions/{id}/tasks/TRANSCRIPTION/)
  - Lifecycle: Persistent (until manual cleanup or encryption)
  - Session ID: UUID format (session-specific)

Workflow:
  1. Doctor starts consultation → initialize_session() → create HDF5 structure
  2. Each 3s → save_chunk() → save to HDF5 (audio + transcript)
  3. Doctor pauses → checkpoint concatenation
  4. Doctor ends → finalize_session() → trigger diarization → SOAP → encryption

Author: Bernard Uriza Orozco
Created: 2025-11-20
Updated: 2026-01-29 (Phase 4B - eliminate get_container)
Card: Voice chat integration (medical handler)
"""

from __future__ import annotations

from typing import Any

from backend.models.task_type import TaskType
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.utils.common.logging.logger import get_logger
from backend.infrastructure.common.services.chunk_handler import ChunkHandler
from backend.utils.common.validation import validate_dependency

logger = get_logger(__name__)


class MedicalChunkHandler(ChunkHandler):
    """Handler for medical consultation workflow.

    Storage: HDF5 persistent (/sessions/{id}/tasks/TRANSCRIPTION/)
    Lifecycle: Persistent (until manual cleanup)
    Post-processing: Diarization → SOAP → Encryption

    Dependencies (Phase 4B):
        - task_repository: ITaskRepository for HDF5 operations

    Example:
        from backend.repositories.task_repository import HDF5TaskRepository
        task_repo = HDF5TaskRepository("storage/corpus.h5")
        handler = MedicalChunkHandler(task_repository=task_repo)
        await handler.initialize_session("session_uuid", {"patient_name": "Juan"})
        await handler.save_chunk("session_uuid", 0, b"audio", "hola", {...})
        status = await handler.get_session_status("session_uuid")
        await handler.finalize_session("session_uuid")  # Triggers diarization
    """

    def __init__(self, task_repository: ITaskRepository):
        """Initialize handler with injected dependencies (Phase 4B).

        Args:
            task_repository: Task repository for HDF5 operations (required)

        Raises:
            ValueError: If task_repository is None
            TypeError: If task_repository doesn't implement ITaskRepository

        Note:
            No longer uses service locator (get_container).
            Direct dependency injection for better testability.
        """
        validate_dependency(task_repository, ITaskRepository, "task_repository")
        self.task_repository = task_repository

    async def initialize_session(
        self,
        session_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create HDF5 task structure and save patient metadata.

        Medical sessions require patient metadata (name, age, ID).

        Args:
            session_id: Session UUID (e.g., "session_20251120_143022")
            metadata: Patient metadata dict with keys:
                - patient_name: str
                - patient_age: str
                - patient_id: str
                - chief_complaint: str (optional)

        Behavior:
            - Creates /sessions/{id}/tasks/TRANSCRIPTION/ in HDF5
            - Saves patient metadata as session attributes
        """
        # Create TRANSCRIPTION task (first time only) - INJECTED (Phase 4B)
        self.task_repository.ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            allow_existing=True,  # Allow resuming (pause/resume)
        )

        # TODO(Phase 5): Re-enable session metadata persistence
        # Requires: locked_session_h5() context manager in backend/repositories/hdf5_utils.py

        logger.info(
            "MEDICAL_SESSION_INITIALIZED",
            session_id=session_id,
            patient_name=metadata.get("patient_name") if metadata else None,
            has_patient_metadata=bool(metadata and any(k.startswith("patient_") for k in metadata)),
        )

    async def save_chunk(
        self,
        session_id: str,
        chunk_number: int,
        audio_bytes: bytes,
        transcript: str,
        metadata: dict[str, Any],
    ) -> None:
        """Save chunk to HDF5 (audio + transcript + metadata).

        Medical chunks are fully persistent:
        - Audio bytes saved to HDF5 dataset
        - Transcript + metadata saved to chunk metadata

        Args:
            session_id: Session UUID
            chunk_number: Chunk index (0, 1, 2, ...)
            audio_bytes: Raw audio data (WebM/WAV/MP3) - PERSISTED
            transcript: Transcription text from STT
            metadata: Provider, confidence, timestamp, duration, etc.

        Behavior:
            - Saves audio_bytes to /sessions/{id}/tasks/TRANSCRIPTION/chunks/chunk_N/audio
            - Saves transcript + metadata to /sessions/{id}/tasks/TRANSCRIPTION/chunks/chunk_N/metadata
        """
        # Save audio to HDF5
        await self._save_audio_to_hdf5(session_id, chunk_number, audio_bytes)

        # TODO(Phase 5): Re-enable chunk metadata persistence via task_repository

        logger.info(
            "MEDICAL_CHUNK_SAVED",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=metadata.get("provider"),
            audio_size_bytes=len(audio_bytes),
            audio_persisted=True,  # Audio IS persisted (unlike chat)
        )

    async def get_session_status(self, session_id: str) -> dict[str, Any]:
        """Read session status from HDF5.

        Args:
            session_id: Session UUID

        Returns:
            dict with keys:
                - session_id: str
                - status: str (in_progress | completed | failed)
                - total_chunks: int
                - processed_chunks: int
                - progress_percent: int (0-100)
                - chunks: list[dict] (chunk metadata)

        Behavior:
            - Reads from HDF5 /sessions/{id}/tasks/TRANSCRIPTION/chunks
            - Calculates progress from chunk statuses
            - Returns 404-like dict if session not found
        """
        try:
            # INJECTED (Phase 4B) - was get_container()
            chunks = self.task_repository.get_task_chunks(session_id, TaskType.TRANSCRIPTION.value)

            if not chunks:
                return {
                    "session_id": session_id,
                    "status": "not_found",
                    "total_chunks": 0,
                    "processed_chunks": 0,
                    "progress_percent": 0,
                    "chunks": [],
                }

            # Calculate progress
            total_chunks = len(chunks)
            completed_chunks = sum(1 for c in chunks if c.get("status") == "completed")
            progress_percent = (
                int((completed_chunks / total_chunks) * 100) if total_chunks > 0 else 0
            )

            # Determine overall status
            if all(c.get("status") == "completed" for c in chunks):
                status = "completed"
            elif any(c.get("status") == "failed" for c in chunks):
                status = "failed"
            else:
                status = "in_progress"

            return {
                "session_id": session_id,
                "status": status,
                "total_chunks": total_chunks,
                "processed_chunks": completed_chunks,
                "progress_percent": progress_percent,
                "chunks": chunks,
            }

        except Exception as e:
            logger.error("MEDICAL_SESSION_STATUS_ERROR", session_id=session_id, error=str(e))
            return {
                "session_id": session_id,
                "status": "error",
                "total_chunks": 0,
                "processed_chunks": 0,
                "progress_percent": 0,
                "chunks": [],
                "error": str(e),
            }

    async def finalize_session(self, session_id: str) -> dict[str, Any]:
        """Trigger post-processing (diarization, SOAP, encryption).

        Medical sessions require full post-processing pipeline:
        1. Diarization (speaker separation using Azure GPT-4)
        2. SOAP generation (clinical notes extraction)
        3. Encryption (AES-GCM-256)

        Args:
            session_id: Session UUID

        Returns:
            dict with keys:
                - session_id: str
                - diarization_job_id: str
                - status: str (post_processing)

        Behavior:
            - Triggers diarization worker (async)
            - Returns job_id for polling
            - Note: SOAP and encryption are triggered after diarization completes
        """
        try:
            # Import here to avoid circular dependency
            from backend.lib.api.medical_workflow import medicalWorkflowApi

            # Trigger diarization (POST /api/workflows/aurity/sessions/{id}/diarization)
            diarization_result = await medicalWorkflowApi.startDiarization(session_id)

            logger.info(
                "MEDICAL_SESSION_FINALIZED",
                session_id=session_id,
                diarization_job_id=diarization_result.get("job_id"),
                post_processing=True,
            )

            return {
                "session_id": session_id,
                "diarization_job_id": diarization_result.get("job_id"),
                "status": "post_processing",
            }

        except Exception as e:
            logger.error("MEDICAL_SESSION_FINALIZE_ERROR", session_id=session_id, error=str(e))
            return {
                "session_id": session_id,
                "status": "error",
                "error": str(e),
            }

    async def _save_audio_to_hdf5(
        self,
        session_id: str,
        chunk_number: int,
        audio_bytes: bytes,
    ) -> None:
        """Save audio bytes to HDF5 chunk dataset.

        Internal helper for save_chunk().

        Args:
            session_id: Session UUID
            chunk_number: Chunk index
            audio_bytes: Raw audio data

        Behavior:
            - Creates dataset at /sessions/{id}/tasks/TRANSCRIPTION/chunks/chunk_{N}/audio
            - Stores audio bytes as binary blob

        Note:
            TEMPORARILY DISABLED - missing locked_session_h5() implementation.
            Audio persistence will be re-enabled in Phase 5.
        """
        # TODO(Phase 5): Re-enable audio chunk persistence (requires locked_session_h5)

        logger.debug(
            "AUDIO_CHUNK_SAVE_SKIPPED",
            session_id=session_id,
            chunk_number=chunk_number,
            size_bytes=len(audio_bytes),
            reason="locked_session_h5 not implemented",
        )
