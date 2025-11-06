"""Diarization API Endpoints (Refactored)

Card: FI-BACKEND-FEAT-004 (refactored 2025-11-05)

Clean Architecture:
- TranscriptionService: Converts audio → raw transcribed segments (Whisper)
- DiarizationService: Enriches segments with speaker ID + text improvement (Ollama)

Endpoints:
- POST /api/diarization/upload - Upload audio, transcribe, diarize
- GET /api/diarization/jobs/{job_id} - Get job status
- GET /api/diarization/result/{job_id} - Get diarization result
- GET /api/diarization/jobs - List jobs
- GET /api/diarization/health - Health check
- POST /api/diarization/soap/{job_id} - Generate SOAP from result

File: backend/api/diarization.py
Created: 2025-10-30
Updated: 2025-11-05 (refactored to use TranscriptionService + DiarizationService)
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel

from backend.container import get_container
from backend.logger import get_logger
from backend.schemas import StatusCode, error_response, success_response
from backend.services.diarization import DiarizationService
from backend.services.diarization.models import DiarizationSegment
from backend.services.soap_generation.service import SOAPGenerationService
from backend.storage.audio_storage import AUDIO_STORAGE_DIR, save_audio_file

# (ruff import sorting - intentional grouping for readability)

logger = get_logger(__name__)

router = APIRouter()

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "ogg", "flac"}


class UploadResponse(BaseModel):
    """Response for upload endpoint."""

    job_id: str
    session_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status endpoint."""

    job_id: str
    session_id: str
    status: str
    progress_pct: int
    total_chunks: int
    processed_chunks: int
    created_at: str
    updated_at: str
    error: str | None = None


class DiarizationSegmentResponse(BaseModel):
    """Single diarization segment."""

    start_time: float
    end_time: float
    speaker: str
    text: str


class DiarizationResultResponse(BaseModel):
    """Complete diarization result."""

    session_id: str
    audio_file_hash: str
    duration_sec: float
    language: str
    model_asr: str
    model_llm: str
    segments: list[DiarizationSegmentResponse]
    processing_time_sec: float
    created_at: str


def _process_diarization_background(
    job_id: str,
    session_id: str,
    audio_path: Path,
    language: str,
    audio_file_hash: str,
    duration_sec: float,
) -> None:
    """Background task: transcribe + diarize audio.

    Steps:
    1. Transcribe audio with TranscriptionService (Whisper)
    2. Diarize segments with DiarizationService (Ollama)
    3. Cache result in job

    Args:
        job_id: Diarization job ID
        session_id: Session identifier
        audio_path: Path to audio file
        language: Language code (es, en, etc.)
        audio_file_hash: SHA256 hash of audio
        duration_sec: Audio duration in seconds
    """
    diarization_service = DiarizationService()
    transcription_service = get_container().get_transcription_service()

    try:
        logger.info(
            "DIARIZATION_JOB_START",
            job_id=job_id,
            session_id=session_id,
            audio_path=str(audio_path),
        )

        # Step 1: Transcribe audio (get raw segments from Whisper)
        diarization_service.update_job(job_id, status="in_progress", progress_percent=10)

        transcription_result = transcription_service.process_transcription(
            session_id=session_id,
            audio_content=audio_path.read_bytes(),
            filename=audio_path.name,
            content_type="audio/mp3",
            metadata={"purpose": "diarization"},
        )

        # Convert transcription segments to DiarizationSegment format
        segments = [
            DiarizationSegment(
                start_time=seg["start"],
                end_time=seg["end"],
                speaker="",
                text=seg["text"],
            )
            for seg in transcription_result.get("segments", [])
        ]

        diarization_service.update_job(
            job_id,
            status="in_progress",
            progress_percent=50,
            total_chunks=len(segments),
        )

        logger.info("TRANSCRIPTION_COMPLETE", job_id=job_id, segment_count=len(segments))

        # Step 2: Diarize segments (add speaker ID + improve text)
        diarization_result = diarization_service.diarize_segments(
            session_id=session_id,
            segments=segments,
            audio_file_path=str(audio_path),
            audio_file_hash=audio_file_hash,
            duration_sec=duration_sec,
            language=language,
        )

        # Step 3: Cache result in job
        diarization_service.update_job(
            job_id,
            status="completed",
            progress_percent=100,
            processed_chunks=len(diarization_result.segments),
            total_chunks=len(diarization_result.segments),
            result_data={
                "session_id": diarization_result.session_id,
                "audio_file_path": diarization_result.audio_file_path,
                "audio_file_hash": diarization_result.audio_file_hash,
                "duration_sec": diarization_result.duration_sec,
                "language": diarization_result.language,
                "segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "speaker": seg.speaker,
                        "text": seg.text,
                        "improved_text": seg.improved_text,
                    }
                    for seg in diarization_result.segments
                ],
                "processing_time_sec": diarization_result.processing_time_sec,
                "created_at": diarization_result.created_at,
                "model_llm": diarization_result.model_llm,
            },
        )

        logger.info(
            "DIARIZATION_JOB_COMPLETE",
            job_id=job_id,
            segment_count=len(diarization_result.segments),
            processing_time=diarization_result.processing_time_sec,
        )

    except Exception as err:
        logger.error(
            "DIARIZATION_JOB_FAILED",
            job_id=job_id,
            session_id=session_id,
            error=str(err),
            traceback=traceback.format_exc(),
        )
        diarization_service.update_job(
            job_id,
            status="failed",
            error_message=str(err),
        )


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_audio_for_diarization(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="Audio file to diarize"),  # noqa: B008
    x_session_id: str | None = Header(None, alias="X-Session-ID"),
    language: str = Query("es", description="Language code"),
) -> Any:
    """Upload audio file and start diarization job (transcribe + diarize).

    Flow:
    1. Save audio file to storage
    2. Create diarization job
    3. Queue background task: TranscriptionService → DiarizationService
    4. Return job_id for polling

    Args:
        audio: Audio file (webm, wav, mp3, m4a, ogg, flac)
        x_session_id: Session ID (required header)
        language: Language code (default: es)
    """
    diarization_service = DiarizationService()
    audit_service = get_container().get_audit_service()

    try:
        # Validate inputs
        if not x_session_id:
            raise ValueError("X-Session-ID header is required")
        if not audio.filename:
            raise ValueError("Audio filename is required")

        # Validate extension
        ext = audio.filename.rsplit(".", 1)[-1].lower() if audio.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension: .{ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # Read audio
        audio_content = await audio.read()

        # Validate size
        if len(audio_content) > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024:.0f}MB limit")

        # Save audio file
        logger.info(
            "AUDIO_SAVE_START",
            session_id=x_session_id,
            filename=audio.filename,
            size=len(audio_content),
        )

        saved_info = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=ext,
            metadata={"original_filename": audio.filename, "purpose": "diarization"},
        )

        audio_path = AUDIO_STORAGE_DIR.parent / saved_info["file_path"]
        audio_hash = saved_info["file_hash"]

        if not audio_path.exists():
            raise OSError(f"Audio file not saved correctly: {audio_path}")

        # Get audio duration (approximate from file size, actual from transcription)
        duration_sec = len(audio_content) / (16000 * 2)

        # Create diarization job
        job_id = diarization_service.create_job(
            session_id=x_session_id,
            audio_file_path=str(audio_path),
            audio_file_size=len(audio_content),
        )

        logger.info(
            "DIARIZATION_JOB_CREATED",
            job_id=job_id,
            session_id=x_session_id,
            audio_path=str(audio_path),
        )

        # Log audit
        audit_service.log_action(
            action="diarization_job_created",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={
                "filename": audio.filename,
                "language": language,
                "session_id": x_session_id,
            },
        )

        # Queue background task: transcribe + diarize
        background_tasks.add_task(
            _process_diarization_background,
            job_id,
            x_session_id,
            audio_path,
            language,
            audio_hash,
            duration_sec,
        )

        # Return job ID
        return success_response(
            {
                "job_id": job_id,
                "session_id": x_session_id,
                "status": "pending",
            },
            message=f"Diarization job created. Poll /api/diarization/jobs/{job_id} for status.",
            code=202,
        )

    except ValueError as err:
        logger.warning("DIARIZATION_VALIDATION_FAILED", error=str(err))
        audit_service.log_action(
            action="diarization_upload_failed",
            user_id="system",
            resource="upload",
            result="failed",
            details={"error": str(err), "session_id": x_session_id},
        )
        return error_response(str(err), code=400, status=StatusCode.VALIDATION_ERROR)

    except OSError as err:
        logger.error("DIARIZATION_STORAGE_FAILED", error=str(err))
        return error_response(
            "Failed to store audio file", code=500, status=StatusCode.INTERNAL_ERROR
        )

    except Exception as err:
        logger.error("DIARIZATION_UPLOAD_FAILED", error=str(err), traceback=traceback.format_exc())
        return error_response("Internal server error", code=500, status=StatusCode.INTERNAL_ERROR)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get status of diarization job.

    Returns job status, progress percentage, and error (if any).
    """
    diarization_service = DiarizationService()
    audit_service = get_container().get_audit_service()

    try:
        job = diarization_service.get_job(job_id)

        if not job:
            logger.warning(f"JOB_NOT_FOUND: job_id={job_id}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        audit_service.log_action(
            action="job_status_retrieved",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"status": job.status},
        )

        logger.info(f"JOB_STATUS_RETRIEVED: job_id={job_id}, status={job.status}")

        return JobStatusResponse(
            job_id=job.job_id,
            session_id=job.session_id,
            status=job.status,
            progress_pct=job.progress_percent,
            total_chunks=job.total_chunks,
            processed_chunks=job.processed_chunks,
            created_at=job.created_at,
            updated_at=job.updated_at,
            error=job.error_message,
        )

    except ValueError as err:
        logger.warning(f"JOB_STATUS_VALIDATION_FAILED: job_id={job_id}, error={err!s}")
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.error(f"JOB_STATUS_FAILED: job_id={job_id}, error={err!s}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status") from err


@router.get("/result/{job_id}", response_model=DiarizationResultResponse)
async def get_diarization_result(job_id: str) -> DiarizationResultResponse:
    """Get diarization result for completed job.

    Returns diarized segments with speaker labels and improved text.
    """
    diarization_service = DiarizationService()
    audit_service = get_container().get_audit_service()

    try:
        job = diarization_service.get_job(job_id)

        if not job or not job.result_data:
            logger.warning(f"DIARIZATION_RESULT_NOT_FOUND: job_id={job_id}")
            raise HTTPException(status_code=404, detail=f"Result not found for job {job_id}")

        result_data = job.result_data

        audit_service.log_action(
            action="diarization_result_retrieved",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"segments": len(result_data.get("segments", []))},
        )

        logger.info(f"DIARIZATION_RESULT_RETRIEVED: job_id={job_id}")

        # Build response
        segments = [
            DiarizationSegmentResponse(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                speaker=seg["speaker"],
                text=seg.get("improved_text", seg["text"]),
            )
            for seg in result_data.get("segments", [])
        ]

        return DiarizationResultResponse(
            session_id=result_data["session_id"],
            audio_file_hash=result_data.get("audio_file_hash", ""),
            duration_sec=result_data["duration_sec"],
            language=result_data.get("language", "es"),
            model_asr="faster-whisper",
            model_llm=result_data.get("model_llm", "qwen2.5:7b-instruct-q4_0"),
            segments=segments,
            processing_time_sec=result_data.get("processing_time_sec", 0.0),
            created_at=result_data["created_at"],
        )

    except ValueError as err:
        logger.warning(f"DIARIZATION_RESULT_VALIDATION_FAILED: job_id={job_id}, error={err!s}")
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        logger.error(f"DIARIZATION_RESULT_FAILED: job_id={job_id}, error={err!s}")
        raise HTTPException(status_code=500, detail="Failed to retrieve result") from err


@router.get("/jobs")
async def list_diarization_jobs(
    session_id: str | None = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> Any:
    """List diarization jobs with optional filtering."""
    from backend.services.diarization.jobs import list_jobs as get_all_jobs

    try:
        jobs = get_all_jobs()

        if session_id:
            jobs = [j for j in jobs if j.session_id == session_id]

        jobs = jobs[:limit]

        logger.info(f"DIARIZATION_JOBS_LISTED: count={len(jobs)}, limit={limit}")

        return success_response(
            [
                {
                    "job_id": j.job_id,
                    "session_id": j.session_id,
                    "status": j.status,
                    "progress_pct": j.progress_percent,
                    "processed_chunks": j.processed_chunks,
                    "total_chunks": j.total_chunks,
                    "created_at": j.created_at,
                    "updated_at": j.updated_at,
                    "error": j.error_message,
                }
                for j in jobs
            ],
            message=f"Found {len(jobs)} jobs",
        )

    except Exception as err:
        logger.error(f"DIARIZATION_JOBS_LIST_FAILED: error={err!s}")
        return success_response([], message="Jobs unavailable")


@router.post("/soap/{job_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def generate_soap_for_job(job_id: str) -> Any:
    """Generate SOAP note from diarization job transcription."""
    try:
        soap_service = SOAPGenerationService()
        soap_note = soap_service.generate_soap_for_job(job_id)

        audit_service = get_container().get_audit_service()
        audit_service.log_action(
            action="soap_generated",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"model": "ollama_mistral_mvp", "completeness": soap_note.completeness},
        )

        logger.info("SOAP_GENERATION_SUCCESS", job_id=job_id, completeness=soap_note.completeness)

        return {
            "job_id": job_id,
            "soap_note": soap_note.model_dump(),
            "status": "success",
            "model": "ollama_mistral_mvp",
        }

    except ValueError as err:
        logger.warning(f"SOAP_GENERATION_VALIDATION_FAILED: job_id={job_id}, error={err!s}")
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        logger.error(f"SOAP_GENERATION_FAILED: job_id={job_id}, error={err!s}")
        raise HTTPException(status_code=500, detail="Failed to generate SOAP note") from err


@router.get("/health")
async def diarization_health() -> Response:
    """Check diarization service health."""
    diarization_service = DiarizationService()

    try:
        health_details = diarization_service.health_check()

        logger.info("DIARIZATION_HEALTH_CHECKED", status=health_details["status"])

        return Response(
            content=json.dumps(health_details),
            media_type="application/json",
            status_code=200 if health_details["status"] == "healthy" else 503,
        )

    except Exception as err:
        logger.error(f"DIARIZATION_HEALTH_CHECK_FAILED: error={err!s}")
        return Response(
            content=json.dumps({"status": "unhealthy", "error": str(err)}),
            media_type="application/json",
            status_code=503,
        )
