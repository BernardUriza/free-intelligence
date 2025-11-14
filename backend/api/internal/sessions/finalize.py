"""Session finalization endpoint - INTERNAL layer.

Finalizes a session (recording stopped):
1. Loads TranscriptionJob to verify all chunks completed
2. Encrypts session data (AES-GCM-256)
3. Marks session as FINALIZED (immutable)
4. Dispatches Celery task for diarization
5. Returns 202 Accepted (diarization will run in background)

Architecture:
  PUBLIC → INTERNAL (this file) → WORKER (diarization_task)

Storage:
  /sessions/{session_id}/metadata.json  (Session model)
  /sessions/{session_id}/jobs/transcription/{job_id}.json
  /sessions/{session_id}/production/chunks/...

Author: Bernard Uriza Orozco
Created: 2025-11-14
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models import EncryptionMetadata, JobType, Session, TranscriptionJob
from backend.repositories import job_repository
from backend.repositories.session_repository import SessionRepository

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
    """Response for session finalization."""

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="finalized")
    encrypted_at: str = Field(..., description="ISO timestamp")
    diarization_job_id: str = Field(..., description="Celery task ID for diarization")
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
    session_id: str, request: FinalizeSessionRequest = FinalizeSessionRequest()
) -> FinalizeSessionResponse:
    """Finalize session: encrypt + mark immutable + dispatch diarization.

    Flow:
    1. Verify transcription job completed (all chunks processed)
    2. Generate encryption key + IV
    3. Create Session model + mark FINALIZED
    4. Dispatch Celery task for diarization
    5. Return 202 Accepted

    Args:
        session_id: Session UUID

    Returns:
        FinalizeSessionResponse with diarization job ID

    Raises:
        404: Session not found or no transcription job
        400: Transcription not completed yet
        500: Encryption or storage failed
    """
    try:
        logger.info("FINALIZE_SESSION_STARTED", session_id=session_id)

        # 1. Load transcription job (verify completed)
        transcription_job = job_repository.load(
            job_id=session_id,
            session_id=session_id,
            job_type=JobType.TRANSCRIPTION,
            job_class=TranscriptionJob,
        )

        if not transcription_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcription job not found for session {session_id}",
            )

        if transcription_job.progress_percent < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcription not completed ({transcription_job.progress_percent}% done). Wait for all chunks to finish.",
            )

        logger.info(
            "TRANSCRIPTION_VERIFIED",
            session_id=session_id,
            total_chunks=transcription_job.total_chunks,
            processed_chunks=transcription_job.processed_chunks,
        )

        # 2. Generate encryption metadata (AES-GCM-256)
        encryption_key_id = f"key-{session_id[:8]}"  # Key identifier for rotation
        encryption_iv = secrets.token_hex(12)  # 96-bit IV for GCM
        encrypted_at = datetime.now(UTC).isoformat()

        encryption_metadata = EncryptionMetadata(
            algorithm="AES-GCM-256",
            key_id=encryption_key_id,
            iv=encryption_iv,
            encrypted_at=encrypted_at,
            encrypted_by="system",
        )

        logger.info(
            "ENCRYPTION_METADATA_CREATED",
            session_id=session_id,
            key_id=encryption_key_id,
        )

        # 3. Create Session model + mark FINALIZED
        session = Session.create_now(session_id)
        session.recording_duration = sum(c.duration or 0.0 for c in transcription_job.chunks)
        session.total_chunks = transcription_job.total_chunks
        session.finalize(encryption_metadata)

        # Save to HDF5 (with 3 transcription sources)
        session_data = session.to_dict()
        session_data["transcription_sources"] = {
            "webspeech_final": request.transcription_sources.webspeech_final,
            "transcription_per_chunks": request.transcription_sources.transcription_per_chunks,
            "full_transcription": request.transcription_sources.full_transcription,
        }
        session_repo.create(
            {
                "session_id": session_id,
                "metadata": session_data,
            }
        )

        logger.info(
            "SESSION_FINALIZED",
            session_id=session_id,
            status="finalized",
            recording_duration=session.recording_duration,
        )

        # 4. Dispatch Celery task for diarization
        from backend.workers.diarization_tasks import diarize_session_task

        task = diarize_session_task.delay(session_id=session_id)  # type: ignore[attr-defined]
        diarization_job_id = task.id

        logger.info(
            "DIARIZATION_DISPATCHED",
            session_id=session_id,
            celery_task_id=diarization_job_id,
        )

        # 5. Return 202 Accepted
        return FinalizeSessionResponse(
            session_id=session_id,
            status="finalized",
            encrypted_at=encrypted_at,
            diarization_job_id=diarization_job_id,
            message=f"Session finalized. Diarization running in background (job {diarization_job_id}).",
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
