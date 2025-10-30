"""
Diarization API Endpoints
Card: FI-BACKEND-FEAT-004

Endpoints:
- POST /api/diarization/upload - Upload audio and start diarization
- GET /api/diarization/jobs/{job_id} - Get job status
- GET /api/diarization/result/{job_id} - Get diarization result
- GET /api/diarization/export/{job_id} - Export result (JSON/MD)
- GET /api/diarization/jobs - List jobs

File: backend/api/diarization.py
Created: 2025-10-30
"""

import os
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Query, BackgroundTasks, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.audio_storage import save_audio_file
from backend.diarization_service import diarize_audio, export_diarization, DiarizationResult
from backend.diarization_jobs import (
    create_job, get_job, update_job_status, list_jobs, JobStatus
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/diarization")

# Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_DIARIZATION_FILE_MB", "100")) * 1024 * 1024  # 100MB
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
    progress_percent: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


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


def _process_diarization_background(job_id: str, audio_path: Path, session_id: str, language: str, persist: bool):
    """
    Background task to process diarization.
    """
    try:
        # Update status to in_progress
        update_job_status(job_id, JobStatus.IN_PROGRESS, progress=10)

        # Create progress callback
        def progress_callback(progress_pct: int):
            update_job_status(job_id, JobStatus.IN_PROGRESS, progress=progress_pct)

        # Run diarization with progress updates
        result = diarize_audio(audio_path, session_id, language, persist, progress_callback=progress_callback)

        # Update status to completed
        update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100,
            result_path=f"/api/diarization/result/{job_id}"
        )

        logger.info("DIARIZATION_JOB_COMPLETED", job_id=job_id, segments=len(result.segments))

    except Exception as e:
        logger.error("DIARIZATION_JOB_FAILED", job_id=job_id, error=str(e))
        update_job_status(job_id, JobStatus.FAILED, error=str(e))


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio_for_diarization(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="Audio file to diarize"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    language: str = Query("es", description="Language code"),
    persist: bool = Query(False, description="Save results to disk")
):
    """
    Upload audio file and start diarization job.

    Returns job_id for tracking progress.
    """
    # Validate session_id
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header required (UUID4 format)"
        )

    # Validate file extension
    if audio.filename:
        ext = audio.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    # Read file
    audio_content = await audio.read()
    file_size = len(audio_content)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )

    logger.info(
        "DIARIZATION_UPLOAD_START",
        session_id=x_session_id,
        filename=audio.filename,
        size=file_size
    )

    # Save audio file
    try:
        saved = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=ext,
            metadata={"original_filename": audio.filename, "purpose": "diarization"}
        )
    except Exception as e:
        logger.error("AUDIO_SAVE_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save audio: {str(e)}"
        )

    # FIX: save_audio_file returns relative path but file is in storage/audio/
    # We need to construct the correct path to the actual file location
    audio_storage_dir = Path(os.getenv("AUDIO_STORAGE_DIR", "./storage/audio"))
    relative_path = saved["file_path"]

    # If path starts with "audio/", prepend "storage/"
    if relative_path.startswith("audio/"):
        audio_path = Path("storage") / relative_path
    else:
        audio_path = Path(relative_path)

    # Make absolute to avoid cwd issues in background tasks
    audio_path = audio_path.absolute()

    # DIAGNOSTIC: Log saved path info
    logger.info(
        "AUDIO_SAVED_FOR_DIARIZATION",
        session_id=x_session_id,
        file_path_raw=saved["file_path"],
        audio_path_str=str(audio_path),
        audio_path_absolute=str(audio_path.absolute()),
        audio_path_exists=audio_path.exists(),
        file_hash=saved.get("file_hash", "N/A"),
        cwd=str(Path.cwd())
    )

    # Create job
    job_id = create_job(x_session_id, str(audio_path), file_size)

    # Schedule background processing
    background_tasks.add_task(
        _process_diarization_background,
        job_id,
        audio_path,
        x_session_id,
        language,
        persist
    )

    return UploadResponse(
        job_id=job_id,
        session_id=x_session_id,
        status="pending",
        message=f"Diarization job created. Poll /api/diarization/jobs/{job_id} for status."
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of diarization job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    return JobStatusResponse(
        job_id=job.job_id,
        session_id=job.session_id,
        status=job.status.value,
        progress_percent=job.progress_percent,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )


@router.get("/result/{job_id}", response_model=DiarizationResultResponse)
async def get_diarization_result(job_id: str):
    """
    Get diarization result for completed job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed. Status: {job.status.value}"
        )

    # Load result from persisted file or re-process
    # For v1, we'll re-run diarization (idempotent)
    try:
        audio_path = Path(job.audio_file_path)
        result = diarize_audio(audio_path, job.session_id, language="es", persist=False)

        return DiarizationResultResponse(
            session_id=result.session_id,
            audio_file_hash=result.audio_file_hash,
            duration_sec=result.duration_sec,
            language=result.language,
            model_asr=result.model_asr,
            model_llm=result.model_llm,
            segments=[
                DiarizationSegmentResponse(
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    speaker=seg.speaker,
                    text=seg.text
                ) for seg in result.segments
            ],
            processing_time_sec=result.processing_time_sec,
            created_at=result.created_at
        )

    except Exception as e:
        logger.error("RESULT_LOAD_FAILED", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load result: {str(e)}"
        )


@router.get("/export/{job_id}")
async def export_diarization_result(
    job_id: str,
    format: str = Query("json", regex="^(json|markdown)$")
):
    """
    Export diarization result in specified format.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed. Status: {job.status.value}"
        )

    try:
        audio_path = Path(job.audio_file_path)
        result = diarize_audio(audio_path, job.session_id, language="es", persist=False)

        content = export_diarization(result, format)

        if format == "json":
            return Response(
                content=content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=diarization_{job_id}.json"
                }
            )
        else:  # markdown
            return Response(
                content=content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f"attachment; filename=diarization_{job_id}.md"
                }
            )

    except Exception as e:
        logger.error("EXPORT_FAILED", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/jobs")
async def list_diarization_jobs(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=100, description="Max results")
):
    """
    List diarization jobs, optionally filtered by session.
    """
    jobs = list_jobs(session_id, limit)

    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "session_id": j.session_id,
                "status": j.status.value,
                "progress_percent": j.progress_percent,
                "created_at": j.created_at,
                "completed_at": j.completed_at
            }
            for j in jobs
        ],
        "count": len(jobs)
    }


@router.get("/health")
async def diarization_health():
    """
    Health check for diarization service.

    Returns:
        - status: operational (all ok) | degraded (whisper ok, llm off/unavailable) | down (whisper unavailable)
        - whisper: bool (ASR availability)
        - llm: bool (Ollama availability)
        - enrichment_enabled: bool (FI_ENRICHMENT status)
    """
    from backend.whisper_service import is_whisper_available
    from backend.diarization_service import check_ollama_available, FI_ENRICHMENT, ENABLE_LLM_CLASSIFICATION

    whisper_ok = is_whisper_available()
    enrichment_enabled = FI_ENRICHMENT and ENABLE_LLM_CLASSIFICATION

    # Check Ollama only if enrichment is enabled
    llm_ok = False
    if enrichment_enabled:
        llm_ok = check_ollama_available()

    # Determine overall status
    if not whisper_ok:
        status_text = "down"  # Critical: ASR unavailable
    elif enrichment_enabled and not llm_ok:
        status_text = "degraded"  # Whisper ok, but LLM enrichment unavailable
    else:
        status_text = "operational"  # All ok (or LLM intentionally disabled)

    return {
        "status": status_text,
        "whisper": whisper_ok,
        "llm": llm_ok,
        "enrichment_enabled": enrichment_enabled,
        "message": f"Diarization service {status_text}"
    }
