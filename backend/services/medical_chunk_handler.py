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
Card: Voice chat integration (medical handler)
"""

from __future__ import annotations

from typing import Any

import h5py

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.services.chunk_handler import ChunkHandler
from backend.storage.task_repository import (
    CORPUS_PATH,
    append_chunk_to_task,
    ensure_task_exists,
    get_task_chunks,
)

logger = get_logger(__name__)


class MedicalChunkHandler(ChunkHandler):
    """Handler for medical consultation workflow.

    Storage: HDF5 persistent (/sessions/{id}/tasks/TRANSCRIPTION/)
    Lifecycle: Persistent (until manual cleanup)
    Post-processing: Diarization → SOAP → Encryption

    Example:
        handler = MedicalChunkHandler()
        await handler.initialize_session("session_uuid", {"patient_name": "Juan"})
        await handler.save_chunk("session_uuid", 0, b"audio", "hola", {...})
        status = await handler.get_session_status("session_uuid")
        await handler.finalize_session("session_uuid")  # Triggers diarization
    """

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
        # Create TRANSCRIPTION task (first time only)
        ensure_task_exists(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            allow_existing=True,  # Allow resuming (pause/resume)
        )

        # Save patient metadata to HDF5 session attributes
        if metadata and any(k.startswith("patient_") for k in metadata.keys()):
            CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with h5py.File(CORPUS_PATH, "a") as f:
                session_path = f"/sessions/{session_id}"
                if session_path not in f:  # type: ignore[operator]
                    session_group = f.create_group(session_path)  # type: ignore[union-attr]
                else:
                    session_group = f[session_path]  # type: ignore[index]

                # Save patient metadata as session attributes
                if "patient_name" in metadata:
                    session_group.attrs["patient_name"] = metadata["patient_name"]
                if "patient_age" in metadata:
                    session_group.attrs["patient_age"] = metadata["patient_age"]
                if "patient_id" in metadata:
                    session_group.attrs["patient_id"] = metadata["patient_id"]
                if "chief_complaint" in metadata:
                    session_group.attrs["chief_complaint"] = metadata["chief_complaint"]

            logger.info(
                "MEDICAL_SESSION_INITIALIZED",
                session_id=session_id,
                patient_name=metadata.get("patient_name"),
                has_patient_metadata=True,
            )
        else:
            logger.info(
                "MEDICAL_SESSION_INITIALIZED",
                session_id=session_id,
                has_patient_metadata=False,
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

        # Save transcript + metadata
        append_chunk_to_task(
            session_id=session_id,
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=chunk_number,
            transcript=transcript,
            audio_hash=str(hash(audio_bytes)),  # Simple hash for deduplication
            duration=metadata.get("duration", 0.0),
            language=metadata.get("language", "es-MX"),
            timestamp_start=metadata.get("timestamp_start", 0.0),
            timestamp_end=metadata.get("timestamp_end", 0.0),
            confidence=metadata.get("confidence", 0.0),
            audio_quality=metadata.get("audio_quality", 0.85),
            provider=metadata.get("provider", "unknown"),
            polling_attempts=metadata.get("polling_attempts", 0),
            resolution_time_seconds=metadata.get("resolution_time_seconds", 0.0),
            retry_attempts=metadata.get("retry_attempts", 0),
        )

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
            chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

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
            progress_percent = int((completed_chunks / total_chunks) * 100) if total_chunks > 0 else 0

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
        """
        CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(CORPUS_PATH, "a") as f:
            audio_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}/chunks/chunk_{chunk_number}/audio"

            # Delete if exists (overwrite)
            if audio_path in f:  # type: ignore[operator]
                del f[audio_path]  # type: ignore[attr-defined]

            # Create dataset with audio bytes
            f.create_dataset(audio_path, data=audio_bytes)  # type: ignore[attr-defined]

        logger.debug(
            "AUDIO_CHUNK_SAVED_TO_HDF5",
            session_id=session_id,
            chunk_number=chunk_number,
            size_bytes=len(audio_bytes),
        )
