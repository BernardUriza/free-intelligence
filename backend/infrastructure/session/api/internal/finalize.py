"""Session finalization endpoint - INTERNAL layer (Async + Outbox Pattern).

Finalizes a session with async encryption queueing.

Python 2026 patterns:
- Annotated[T, Depends(...)] for cleaner DI
- `|` union syntax for type hints
- match/case for cleaner error handling
- Path with tempfile for safe temp directory handling

Flow:
1. Verifies TRANSCRIPTION task completed (all chunks have transcripts)
2. Saves 3 transcription sources to HDF5 (WebSpeech, Chunks, Full)
3. Marks session as FINALIZED (immutable)
4. Enqueues ENCRYPTION task asynchronously (non-blocking)
5. Returns 202 Accepted immediately

Async Pattern:
  - finalize() returns 202 ACCEPTED instantly
  - Encryption queued via ThreadPoolExecutor (fire-and-forget)
  - Idempotent: multiple calls return same result
  - Graceful degradation: session FINALIZED even if encryption enqueue fails

NOTE: This should only be called AFTER SOAP generation is complete.

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/session/internal/sessions/finalize.py
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.config import CORPUS_PATH
from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.infrastructure.workers.executor_pool import spawn_worker
from backend.infrastructure.workers.tasks.encryption.worker import encrypt_session_worker
from backend.models import EncryptionMetadata, Session
from backend.models.task_type import TaskStatus, TaskType
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.repositories.session_repository import SessionRepository
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["internal-sessions"])

session_repo = SessionRepository(str(CORPUS_PATH))


class TranscriptionSources(BaseModel):
    """3 separate transcription sources for LLM analysis."""

    webspeech_final: list[str] = Field(default_factory=list, description="WebSpeech instant previews")
    transcription_per_chunks: list[dict[str, Any]] = Field(default_factory=list, description="Whisper per-chunk transcripts")
    full_transcription: str = Field(default="", description="Concatenated full text")


class FinalizeSessionRequest(BaseModel):
    """Request for session finalization."""

    transcription_sources: TranscriptionSources = Field(
        default_factory=TranscriptionSources,
        description="3 separate transcription sources",
    )


class FinalizeSessionResponse(BaseModel):
    """Response for session finalization (202 Accepted)."""

    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="ACCEPTED (session finalized, encryption queued)")
    finalized_at: str = Field(..., description="ISO timestamp of finalization")
    encryption_status: str = Field(..., description="PENDING | QUEUED | ENQUEUE_FAILED")
    encryption_task_id: str | None = Field(None, description="ENCRYPTION task idempotency key")
    diarization_job_id: str | None = Field(None, description="Deprecated - use /diarization endpoint")
    message: str = Field(..., description="Human-readable message")


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=FinalizeSessionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def finalize_session(
    session_id: str,
    task_repo: Annotated[ITaskRepository, Depends(get_task_repository)],
    audit_service: Annotated[DIAuditService, Depends(get_audit_service)],
    current_user: Annotated[User, Depends(get_current_user)],
    request: FinalizeSessionRequest | None = None,
) -> FinalizeSessionResponse:
    """Finalize session with async encryption queueing (202 Accepted).

    Flow:
    1. Verify TRANSCRIPTION task completed (100%)
    2. Verify required tasks (DIARIZATION, SOAP_GENERATION)
    3. Save 3 transcription sources to HDF5
    4. Concatenate audio chunks -> full_audio.webm
    5. Mark session as FINALIZED
    6. Enqueue ENCRYPTION task asynchronously (fire-and-forget)
    7. Return 202 ACCEPTED immediately (non-blocking)

    Args:
        session_id: Session UUID
        task_repo: Task repository (injected)
        audit_service: Audit service (injected)
        current_user: Authenticated user (injected)
        request: Optional FinalizeSessionRequest with transcription sources

    Returns:
        FinalizeSessionResponse with encryption status

    Raises:
        404: Session not found or no TRANSCRIPTION task
        400: Transcription not completed or required tasks missing
        500: Finalization failed
    """
    if request is None:
        request = FinalizeSessionRequest()

    try:
        logger.info("FINALIZE_SESSION_STARTED", session_id=session_id)

        # 1. Verify TRANSCRIPTION task exists and get chunks
        task_metadata = task_repo.get_task_metadata(session_id, TaskType.TRANSCRIPTION)
        if not task_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"TRANSCRIPTION task not found for session {session_id}",
            )

        chunks = task_repo.get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No transcription chunks found for session {session_id}",
            )

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

        # 1.5. Verify REQUIRED tasks are completed before encryption
        required_tasks = {
            TaskType.DIARIZATION: "Diarization (speaker identification) must be completed",
            TaskType.SOAP_GENERATION: "SOAP note generation must be completed",
        }

        missing_tasks = []
        incomplete_tasks = []

        for task_type, description in required_tasks.items():
            try:
                task_meta = task_repo.get_task_metadata(session_id, task_type)
                if not task_meta:
                    missing_tasks.append(f"{task_type}: {description}")
                    continue

                task_status = task_meta.get("status", "pending")
                if task_status != TaskStatus.COMPLETED:
                    incomplete_tasks.append(f"{task_type}: status={task_status} (expected: completed)")
            except ValueError:
                missing_tasks.append(f"{task_type}: {description}")

        if missing_tasks or incomplete_tasks:
            error_details = []
            if missing_tasks:
                error_details.append("Missing tasks: " + ", ".join(missing_tasks))
            if incomplete_tasks:
                error_details.append("Incomplete tasks: " + ", ".join(incomplete_tasks))

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot finalize session - required tasks not completed. {' | '.join(error_details)}",
            )

        logger.info("REQUIRED_TASKS_VERIFIED", session_id=session_id, tasks_verified=list(required_tasks.keys()))

        # 2. Initialize ENCRYPTION task
        task_repo.ensure_task_exists(session_id, TaskType.ENCRYPTION.value, metadata=None)
        task_repo.save_task_metadata(
            session_id,
            TaskType.ENCRYPTION.value,
            {
                "status": TaskStatus.PENDING,
                "progress_percent": 0,
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "note": "Encryption will execute after SOAP generation completes",
            },
        )

        encryption_key_id = f"pending-{session_id[:8]}"
        encrypted_at = datetime.now(timezone.utc).isoformat()

        encryption_metadata = EncryptionMetadata(
            algorithm="AES-GCM-256",
            key_id=encryption_key_id,
            iv="pending",
            encrypted_at=encrypted_at,
            encrypted_by="system",
        )

        logger.info("ENCRYPTION_TASK_INITIALIZED", session_id=session_id, status="PENDING")

        # 3. Create Session model + mark FINALIZED
        session = Session.create_now(session_id)
        session.recording_duration = sum(c.get("duration", 0.0) for c in chunks)
        session.total_chunks = total_chunks
        session.finalize(encryption_metadata)

        session_data = session.to_dict()
        existing_session = session_repo.read(session_id)

        if existing_session:
            session_repo.update(session_id, {"session_id": session_id, "metadata": session_data})
            audit_service.log_action(
                action="session_updated",
                user_id=current_user.id,
                clinic_id=None,
                resource=session_id,
                result="success"
            )
        else:
            session_repo.create({"session_id": session_id, "metadata": session_data})
            audit_service.log_action(
                action="session_created",
                user_id=current_user.id,
                clinic_id=None,
                resource=session_id,
                result="success"
            )

        # Save 3 transcription sources to TRANSCRIPTION task
        try:
            if request.transcription_sources.webspeech_final:
                task_repo.add_webspeech_transcripts(
                    session_id=session_id,
                    transcripts=request.transcription_sources.webspeech_final,
                    task_type=TaskType.TRANSCRIPTION,
                )
                logger.info("WEBSPEECH_SAVED", session_id=session_id, count=len(request.transcription_sources.webspeech_final))

            if request.transcription_sources.full_transcription:
                task_repo.add_full_transcription(
                    session_id=session_id,
                    full_text=request.transcription_sources.full_transcription,
                    task_type=TaskType.TRANSCRIPTION,
                )
                logger.info("FULL_TRANSCRIPTION_SAVED", session_id=session_id, length=len(request.transcription_sources.full_transcription))

            # Concatenate audio chunks into full_audio.webm
            _concatenate_audio_chunks(session_id, task_repo, audit_service, current_user)

            logger.info(
                "3_SOURCES_SAVED",
                session_id=session_id,
                webspeech_count=len(request.transcription_sources.webspeech_final),
                chunks_count=len(request.transcription_sources.transcription_per_chunks),
                full_length=len(request.transcription_sources.full_transcription),
            )

        except ValueError as e:
            audit_service.log_action(
                action="transcription_sources_save_failed",
                user_id=current_user.id,
                resource=session_id,
                result="failure",
                details={"error": str(e)},
            )

        logger.info(
            "SESSION_FINALIZED",
            session_id=session_id,
            status="finalized",
            recording_duration=session.recording_duration,
        )

        # 4. Enqueue encryption worker asynchronously (NON-BLOCKING)
        h5_path = str(CORPUS_PATH)
        encryption_task_id = f"encrypt:{session_id}"
        encryption_status = "PENDING"

        try:
            spawn_worker(
                encrypt_session_worker,
                session_id=session_id,
                h5_path=h5_path,
                task_repo=task_repo,
                targets=None,
            )
            encryption_status = "QUEUED"
            logger.info("ENCRYPTION_ENQUEUED", session_id=session_id, encryption_task_id=encryption_task_id, status="QUEUED")

        except Exception as enqueue_err:
            encryption_status = "ENQUEUE_FAILED"
            audit_service.log_action(
                action="encryption_enqueue_failed",
                user_id=current_user.id,
                resource=session_id,
                result="failure",
                details={"error": str(enqueue_err), "encryption_task_id": encryption_task_id},
            )

        # 5. Return 202 Accepted IMMEDIATELY
        return FinalizeSessionResponse(
            session_id=session_id,
            status="ACCEPTED",
            finalized_at=encrypted_at,
            encryption_status=encryption_status,
            encryption_task_id=encryption_task_id if encryption_status == "QUEUED" else None,
            diarization_job_id=None,
            message=f"Session finalized. Encryption {encryption_status.lower()}.",
        )

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="session_finalization_failed",
            user_id=current_user.id,
            resource=session_id,
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize session: {e!s}",
        ) from e


def _concatenate_audio_chunks(
    session_id: str,
    task_repo: ITaskRepository,
    audit_service: DIAuditService,
    current_user: User,
) -> None:
    """Concatenate audio chunks into full_audio.webm using ffmpeg."""
    try:
        chunks_with_audio = task_repo.get_task_chunks(session_id, TaskType.TRANSCRIPTION)

        if not chunks_with_audio:
            logger.warning("NO_CHUNKS_FOR_CONCATENATION", session_id=session_id)
            return

        temp_dir = Path(tempfile.mkdtemp(prefix="audio_concat_"))
        audio_files = []

        for chunk in sorted(chunks_with_audio, key=lambda x: x["chunk_idx"]):
            chunk_idx = chunk["chunk_idx"]
            audio_bytes = task_repo.get_chunk_audio_bytes(
                session_id=session_id,
                task_type=TaskType.TRANSCRIPTION.name,
                chunk_idx=chunk_idx
            )

            if audio_bytes:
                temp_audio = temp_dir / f"chunk_{chunk_idx:03d}.webm"
                temp_audio.write_bytes(audio_bytes)
                audio_files.append(temp_audio)

        if not audio_files:
            logger.warning("NO_AUDIO_CHUNKS_FOUND", session_id=session_id, reason="Chunks exist but have no audio.webm files")
            return

        concat_list = temp_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file}'\n")

        output_file = temp_dir / "full_audio.webm"
        ffmpeg_cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(concat_list), "-c", "copy",
            str(output_file), "-loglevel", "error", "-y",
        ]

        subprocess.run(ffmpeg_cmd, check=True, timeout=60)

        full_audio_bytes = output_file.read_bytes()

        task_repo.add_full_audio(
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

        shutil.rmtree(temp_dir)

    except Exception as concat_err:
        audit_service.log_action(
            action="audio_concatenation_failed",
            user_id=current_user.id,
            resource=session_id,
            result="failure",
            details={"error": str(concat_err)},
        )
