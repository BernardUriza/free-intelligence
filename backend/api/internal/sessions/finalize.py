"""Session finalization endpoint - INTERNAL layer (Async + Outbox Pattern).

Finalizes a session with async encryption queueing:
1. Verifies TRANSCRIPTION task completed (all chunks have transcripts)
2. Saves 3 transcription sources to HDF5 (WebSpeech, Chunks, Full)
3. Marks session as FINALIZED (immutable)
4. Enqueues ENCRYPTION task asynchronously (non-blocking)
5. Returns 202 Accepted immediately

**Async Pattern:**
  - finalize() returns 202 ACCEPTED instantly
  - Encryption queued via ThreadPoolExecutor (fire-and-forget)
  - Idempotent: multiple calls return same result
  - Graceful degradation: session FINALIZED even if encryption enqueue fails

**Outbox Pattern** (future):
  - Persist outbox event in HDF5 for retry
  - Background worker processes outbox events
  - Guarantees eventual encryption execution

NOTE: This should only be called AFTER SOAP generation is complete.
      Diarization is now a separate endpoint: /sessions/{id}/diarization

Architecture:
  PUBLIC → INTERNAL (this file) → ThreadPoolExecutor → encryption_worker

Storage (Task-based schema):
  /sessions/{session_id}/tasks/TRANSCRIPTION/
    ├─ chunks/chunk_{idx}/  (Whisper transcripts + audio)
    ├─ webspeech_final      (WebSpeech previews)
    ├─ full_transcription   (concatenated text)
    └─ job_metadata         (task metadata)

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-11-18 (Async encryption with outbox pattern)
"""

from __future__ import annotations

import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models import EncryptionMetadata, Session
from backend.models.task_type import TaskStatus, TaskType
from backend.repositories.session_repository import SessionRepository
from backend.storage.task_repository import (
    add_full_audio,
    add_full_transcription,
    add_webspeech_transcripts,
    get_task_chunks,
    get_task_metadata,
    update_task_metadata,
)
from backend.workers.executor_pool import spawn_worker
from backend.workers.tasks.encryption_worker import encrypt_session_worker

logger = get_logger(__name__)

router = APIRouter(tags=["internal-sessions"])

# Initialize session repository
session_repo = SessionRepository(
    "/Users/bernardurizaorozco/Documents/free-intelligence/storage/corpus.h5"
)


# ============================================================================
# Request/Response Models
# ============================================================================


class TranscriptionSources(BaseModel):
    """3 separate transcription sources for LLM analysis."""

    webspeech_final: list[str] = Field(
        default_factory=list, description="WebSpeech instant previews"
    )
    transcription_per_chunks: list[dict[str, Any]] = Field(
        default_factory=list, description="Whisper per-chunk transcripts"
    )
    full_transcription: str = Field(default="", description="Concatenated full text")


class FinalizeSessionRequest(BaseModel):
    """Request for session finalization."""

    transcription_sources: TranscriptionSources = Field(
        default_factory=TranscriptionSources,
        description="3 separate transcription sources",
    )


class FinalizeSessionResponse(BaseModel):
    """Response for session finalization (202 Accepted).

    Returns immediately with encryption queued asynchronously.
    """

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="ACCEPTED (session finalized, encryption queued)")
    finalized_at: str = Field(..., description="ISO timestamp of finalization")
    encryption_status: str = Field(..., description="PENDING | QUEUED | ENQUEUE_FAILED")
    encryption_task_id: str | None = Field(
        None, description="ENCRYPTION task idempotency key (for tracking)"
    )
    diarization_job_id: str | None = Field(
        None, description="Deprecated - use /diarization endpoint instead"
    )
    message: str = Field(..., description="Human-readable message")


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=FinalizeSessionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def finalize_session(
    session_id: str,
    request: FinalizeSessionRequest | None = None,
) -> FinalizeSessionResponse:
    """Finalize session with async encryption queueing (202 Accepted).

    **Flow:**
    1. Verify TRANSCRIPTION task completed (100%)
    2. Save 3 transcription sources to HDF5
    3. Concatenate audio chunks → full_audio.webm
    4. Mark session as FINALIZED
    5. Enqueue ENCRYPTION task asynchronously (fire-and-forget)
    6. Return 202 ACCEPTED immediately (non-blocking)

    **Async Pattern:**
    - Returns 202 instantly (client doesn't wait for encryption)
    - Encryption executes in background ThreadPoolExecutor
    - Client can poll /sessions/{id}/tasks/ENCRYPTION for progress
    - Idempotent: multiple calls return same result

    **Graceful Degradation:**
    - Session FINALIZED even if encryption enqueue fails
    - Encryption will retry via outbox pattern (future)

    NOTE: This should only be called AFTER SOAP generation is complete.

    Flow:
    1. Verify TRANSCRIPTION task exists and all chunks completed
    2. Save 3 transcription sources to HDF5 (WebSpeech, Chunks, Full)
    3. Generate encryption key + IV
    4. Create Session model + mark FINALIZED
    5. Return 202 Accepted

    Args:
        session_id: Session UUID
        request: FinalizeSessionRequest with 3 transcription sources

    Returns:
        FinalizeSessionResponse with encrypted_at timestamp

    Raises:
        404: Session not found or no TRANSCRIPTION task
        400: Transcription not completed yet
        500: Encryption or storage failed
    """
    # Initialize request if None
    if request is None:
        request = FinalizeSessionRequest()

    try:
        logger.info("FINALIZE_SESSION_STARTED", session_id=session_id)

        # 1. Verify TRANSCRIPTION task exists and get chunks
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not task_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"TRANSCRIPTION task not found for session {session_id}",
            )

        # Get all chunks to verify completion
        chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No transcription chunks found for session {session_id}",
            )

        # Check if all chunks are completed (have transcripts)
        total_chunks = len(chunks)
        completed_chunks = sum(1 for c in chunks if c.get("transcript"))
        progress_percent = (completed_chunks / total_chunks * 100) if total_chunks > 0 else 0

        if progress_percent < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcription not completed ({progress_percent:.0f}% done, {completed_chunks}/{total_chunks} chunks). Wait for all chunks to finish.",
            )

        logger.info(
            "TRANSCRIPTION_VERIFIED",
            session_id=session_id,
            total_chunks=total_chunks,
            completed_chunks=completed_chunks,
        )

        # 2. Initialize ENCRYPTION task (metadata only - actual encryption happens after SOAP)
        # This creates the task entry in HDF5 for tracking
        from backend.storage.task_repository import ensure_task_exists

        ensure_task_exists(session_id, TaskType.ENCRYPTION, allow_existing=True)
        update_task_metadata(
            session_id,
            TaskType.ENCRYPTION,
            {
                "status": TaskStatus.PENDING,
                "progress_percent": 0,
                "queued_at": datetime.now(UTC).isoformat(),
                "note": "Encryption will execute after SOAP generation completes",
            },
        )

        # Placeholder encryption metadata for Session model (legacy)
        encryption_key_id = f"pending-{session_id[:8]}"
        encryption_iv = "pending"
        encrypted_at = datetime.now(UTC).isoformat()

        encryption_metadata = EncryptionMetadata(
            algorithm="AES-GCM-256",
            key_id=encryption_key_id,
            iv=encryption_iv,
            encrypted_at=encrypted_at,
            encrypted_by="system",
        )

        logger.info(
            "ENCRYPTION_TASK_INITIALIZED",
            session_id=session_id,
            status="PENDING",
            note="Actual encryption deferred until after SOAP",
        )

        # 3. Create Session model + mark FINALIZED
        session = Session.create_now(session_id)
        session.recording_duration = sum(c.get("duration", 0.0) for c in chunks)
        session.total_chunks = total_chunks
        session.finalize(encryption_metadata)

        # Save session to HDF5 (update if exists, create if not)
        session_data = session.to_dict()
        existing_session = session_repo.read(session_id)

        if existing_session:
            # Session exists, update it
            session_repo.update(
                session_id,
                {
                    "session_id": session_id,
                    "metadata": session_data,
                },
            )
            logger.info("SESSION_UPDATED", session_id=session_id)
        else:
            # Session doesn't exist, create it
            session_repo.create(
                {
                    "session_id": session_id,
                    "metadata": session_data,
                }
            )
            logger.info("SESSION_CREATED", session_id=session_id)

        # Save 3 transcription sources to TRANSCRIPTION task (NEW schema)
        try:
            # 1. WebSpeech instant previews
            if request.transcription_sources.webspeech_final:
                add_webspeech_transcripts(
                    session_id=session_id,
                    transcripts=request.transcription_sources.webspeech_final,
                    task_type=TaskType.TRANSCRIPTION,
                )
                logger.info(
                    "WEBSPEECH_SAVED",
                    session_id=session_id,
                    count=len(request.transcription_sources.webspeech_final),
                )

            # 2. Full concatenated transcription
            if request.transcription_sources.full_transcription:
                add_full_transcription(
                    session_id=session_id,
                    full_text=request.transcription_sources.full_transcription,
                    task_type=TaskType.TRANSCRIPTION,
                )
                logger.info(
                    "FULL_TRANSCRIPTION_SAVED",
                    session_id=session_id,
                    length=len(request.transcription_sources.full_transcription),
                )

            # 3. Per-chunk transcripts already saved by worker (chunks/ directory)

            # 4. Concatenate audio chunks into full_audio.webm (backend concatenation)
            try:
                import h5py

                # Read all chunks with audio from HDF5
                chunks_with_audio = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

                if chunks_with_audio:
                    # Create temp directory for audio extraction
                    temp_dir = Path(tempfile.mkdtemp(prefix="audio_concat_"))
                    audio_files = []

                    # Extract audio from each chunk
                    with h5py.File(
                        Path(__file__).parent.parent.parent.parent / "storage" / "corpus.h5", "r"
                    ) as f:
                        for chunk in sorted(chunks_with_audio, key=lambda x: x["chunk_idx"]):
                            chunk_idx = chunk["chunk_idx"]
                            chunk_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{chunk_idx}"

                            if chunk_path in f:
                                chunk_group = f[chunk_path]

                                # Check if audio.webm exists
                                if "audio.webm" in chunk_group:
                                    audio_bytes = chunk_group["audio.webm"][()]

                                    # Save to temp file
                                    temp_audio = temp_dir / f"chunk_{chunk_idx:03d}.webm"
                                    temp_audio.write_bytes(audio_bytes)
                                    audio_files.append(temp_audio)

                    if audio_files:
                        # Create ffmpeg concat file list
                        concat_list = temp_dir / "concat_list.txt"
                        with open(concat_list, "w") as f:
                            for audio_file in audio_files:
                                f.write(f"file '{audio_file}'\n")

                        # Concatenate using ffmpeg
                        output_file = temp_dir / "full_audio.webm"
                        ffmpeg_cmd = [
                            "ffmpeg",
                            "-f",
                            "concat",
                            "-safe",
                            "0",
                            "-i",
                            str(concat_list),
                            "-c",
                            "copy",
                            str(output_file),
                            "-loglevel",
                            "error",
                            "-y",
                        ]

                        subprocess.run(ffmpeg_cmd, check=True, timeout=60)

                        # Read concatenated audio
                        full_audio_bytes = output_file.read_bytes()

                        # Save to HDF5
                        add_full_audio(
                            session_id=session_id,
                            audio_bytes=full_audio_bytes,
                            filename="full_audio.webm",
                            task_type=TaskType.TRANSCRIPTION,
                        )

                        logger.info(
                            "FULL_AUDIO_CONCATENATED",
                            session_id=session_id,
                            chunks_concatenated=len(audio_files),
                            size_bytes=len(full_audio_bytes),
                        )

                        # Cleanup temp files
                        import shutil

                        shutil.rmtree(temp_dir)
                    else:
                        logger.warning(
                            "NO_AUDIO_CHUNKS_FOUND",
                            session_id=session_id,
                            reason="Chunks exist but have no audio.webm files",
                        )
                else:
                    logger.warning(
                        "NO_CHUNKS_FOR_CONCATENATION",
                        session_id=session_id,
                    )

            except Exception as concat_err:
                logger.error(
                    "AUDIO_CONCATENATION_FAILED",
                    session_id=session_id,
                    error=str(concat_err),
                    exc_info=True,
                )
                # Don't fail finalization if concatenation fails

            logger.info(
                "3_SOURCES_SAVED",
                session_id=session_id,
                webspeech_count=len(request.transcription_sources.webspeech_final),
                chunks_count=len(request.transcription_sources.transcription_per_chunks),
                full_length=len(request.transcription_sources.full_transcription),
            )

        except ValueError as e:
            logger.error(
                "TRANSCRIPTION_SOURCES_SAVE_FAILED",
                session_id=session_id,
                error=str(e),
            )
            # Don't fail the entire finalization if sources save fails
            # The session is still finalized, just missing the 3 sources

        logger.info(
            "SESSION_FINALIZED",
            session_id=session_id,
            status="finalized",
            recording_duration=session.recording_duration,
        )

        # 4. Enqueue encryption worker asynchronously (NON-BLOCKING)
        # Fire-and-forget pattern: session returns 202 immediately
        # Encryption executes in background ThreadPoolExecutor
        from backend.storage.task_repository import CORPUS_PATH
        h5_path = str(CORPUS_PATH)

        # Get idempotency key from ENCRYPTION task
        encryption_task_id = f"encrypt:{session_id}"
        encryption_status = "PENDING"

        try:
            # Spawn worker asynchronously (fire-and-forget)
            spawn_worker(
                encrypt_session_worker,
                session_id=session_id,
                h5_path=h5_path,
                targets=None,  # Use default targets from worker
            )

            encryption_status = "QUEUED"

            logger.info(
                "ENCRYPTION_ENQUEUED",
                session_id=session_id,
                encryption_task_id=encryption_task_id,
                h5_path=h5_path,
                status="QUEUED",
            )

        except Exception as enqueue_err:
            # Graceful degradation: session still FINALIZED
            # Worker will retry via outbox pattern (future)
            encryption_status = "ENQUEUE_FAILED"

            logger.error(
                "ENCRYPTION_ENQUEUE_FAILED",
                session_id=session_id,
                encryption_task_id=encryption_task_id,
                error=str(enqueue_err),
                exc_info=True,
            )
            # Don't fail finalization - encryption will retry via outbox

        # 5. Return 202 Accepted IMMEDIATELY (async pattern)
        # Client doesn't wait for encryption to complete
        return FinalizeSessionResponse(
            session_id=session_id,
            status="ACCEPTED",
            finalized_at=encrypted_at,
            encryption_status=encryption_status,
            encryption_task_id=encryption_task_id if encryption_status == "QUEUED" else None,
            diarization_job_id=None,  # Not dispatched here anymore
            message=f"Session finalized. Encryption {encryption_status.lower()}.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "FINALIZE_SESSION_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {e!s}",
        ) from e
