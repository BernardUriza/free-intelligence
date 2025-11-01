"""
Diarization API Endpoints
Card: FI-BACKEND-FEAT-004 + FI-RELIABILITY-IMPL-004

Endpoints:
- POST /api/diarization/upload - Upload audio and start diarization (low-priority worker)
- GET /api/diarization/jobs/{job_id} - Get job status with chunks[] from HDF5
- GET /api/diarization/result/{job_id} - Get diarization result
- GET /api/diarization/export/{job_id} - Export result (JSON/MD)
- GET /api/diarization/jobs - List jobs

Low-Priority Worker:
- CPU scheduler: only processes when CPU idle ≥50% for 10s
- Incremental HDF5 storage (storage/diarization.h5)
- Per-chunk progress updates
- Does NOT block Triage/Timeline APIs

File: backend/api/diarization.py
Created: 2025-10-30
Updated: 2025-10-31
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional, Union

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
from pydantic import BaseModel, Field

from backend.audio_storage import save_audio_file
from backend.diarization_jobs import (
    JobStatus,
    create_job,
    get_job,
    list_jobs,
    update_job_status,
)
from backend.diarization_service import (
    DiarizationResult,
    diarize_audio,
    export_diarization,
)
from backend.diarization_service_v2 import diarize_audio_parallel
from backend.diarization_worker_lowprio import (
    create_diarization_job as create_lowprio_job,
)
from backend.diarization_worker_lowprio import get_job_status as get_lowprio_status
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/diarization")

# Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_DIARIZATION_FILE_MB", "100")) * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "ogg", "flac"}
USE_V2_PIPELINE = (
    os.getenv("DIARIZATION_USE_V2", "true").lower() == "true"
)  # Use optimized pipeline
USE_LOWPRIO_WORKER = (
    os.getenv("DIARIZATION_LOWPRIO", "true").lower() == "true"
)  # Use low-priority worker


class UploadResponse(BaseModel):
    """Response for upload endpoint."""

    job_id: str
    session_id: str
    status: str
    message: str


class ChunkInfo(BaseModel):
    """Chunk information with incremental results."""

    chunk_idx: int
    start_time: float
    end_time: float
    text: str
    speaker: str
    temperature: float
    rtf: float
    timestamp: str


class JobStatusResponse(BaseModel):
    """Response for job status endpoint (with chunks array)."""

    job_id: str
    session_id: str
    status: str
    progress_pct: int
    total_chunks: int
    processed_chunks: int
    chunks: list[ChunkInfo] = Field(default_factory=list)
    created_at: str
    updated_at: str
    error: Optional[str] = None


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


def _process_diarization_background_v2(
    job_id: str, audio_path: Path, session_id: str, language: str, persist: bool
):
    """
    Background task wrapper for V2 optimized pipeline.

    This is a SYNC function that runs the async pipeline using asyncio.run().
    Required because FastAPI BackgroundTasks.add_task() doesn't support async functions directly.
    """
    import asyncio

    async def _async_pipeline():
        try:
            # Update status to in_progress
            update_job_status(
                job_id, JobStatus.IN_PROGRESS, progress=10, last_event="DIARIZATION_STARTED_V2"
            )

            # Create progress callback
            def progress_callback(
                progress_pct: int, processed: int = 0, total: int = 0, event: str = ""
            ):
                update_job_status(
                    job_id,
                    JobStatus.IN_PROGRESS,
                    progress=progress_pct,
                    processed=processed,
                    total=total,
                    last_event=event or f"PROCESSING_CHUNK_{processed}",
                )

            # Run optimized diarization pipeline
            result = await diarize_audio_parallel(
                audio_path, session_id, language, persist, progress_callback
            )

            # Cache result in job (no re-processing needed)
            update_job_status(
                job_id,
                JobStatus.COMPLETED,
                progress=100,
                result_path=f"/api/diarization/result/{job_id}",
                processed=len(result.segments),
                total=len(result.segments),
                last_event="DIARIZATION_COMPLETED_V2",
                result_data=asdict(result),  # Cache full result
            )

            logger.info(
                "DIARIZATION_JOB_COMPLETED_V2", job_id=job_id, segments=len(result.segments)
            )

        except Exception as e:
            logger.error("DIARIZATION_JOB_FAILED_V2", job_id=job_id, error=str(e))
            update_job_status(
                job_id, JobStatus.FAILED, error=str(e), last_event="DIARIZATION_FAILED_V2"
            )

    # Run async pipeline in sync context
    asyncio.run(_async_pipeline())


def _process_diarization_background(
    job_id: str, audio_path: Path, session_id: str, language: str, persist: bool
):
    """
    Background task wrapper for V1 (legacy) pipeline.
    Kept for backward compatibility.
    """
    try:
        update_job_status(
            job_id, JobStatus.IN_PROGRESS, progress=10, last_event="DIARIZATION_STARTED"
        )

        def progress_callback(
            progress_pct: int, processed: int = 0, total: int = 0, event: str = ""
        ):
            update_job_status(
                job_id,
                JobStatus.IN_PROGRESS,
                progress=progress_pct,
                processed=processed,
                total=total,
                last_event=event or f"PROCESSING_CHUNK_{processed}",
            )

        result = diarize_audio(
            audio_path, session_id, language, persist, progress_callback=progress_callback
        )

        update_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100,
            result_path=f"/api/diarization/result/{job_id}",
            processed=len(result.segments),
            total=len(result.segments),
            last_event="DIARIZATION_COMPLETED",
            result_data=asdict(result),
        )

        logger.info("DIARIZATION_JOB_COMPLETED", job_id=job_id, segments=len(result.segments))

    except Exception as e:
        logger.error("DIARIZATION_JOB_FAILED", job_id=job_id, error=str(e))
        update_job_status(job_id, JobStatus.FAILED, error=str(e), last_event="DIARIZATION_FAILED")


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_audio_for_diarization(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="Audio file to diarize"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    language: str = Query("es", description="Language code"),
    persist: bool = Query(False, description="Save results to disk"),
    whisper_model: Optional[str] = Query(
        None, description="Whisper model: tiny, base, small, medium, large-v3"
    ),
    enable_llm_classification: Optional[bool] = Query(
        None, description="Enable LLM speaker classification"
    ),
    chunk_size_sec: Optional[int] = Query(None, description="Audio chunk size in seconds"),
    beam_size: Optional[int] = Query(None, description="Whisper beam size"),
    vad_filter: Optional[bool] = Query(None, description="Enable Voice Activity Detection"),
):
    """
    Upload audio file and start diarization job.

    Low-priority mode (DIARIZATION_LOWPRIO=true):
    - Uses CPU scheduler (only runs when CPU idle ≥50%)
    - Saves chunks incrementally to HDF5
    - Does NOT block main thread

    Returns job_id for tracking progress.
    """
    # Validate session_id
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Session-ID header required (UUID4 format)",
        )

    # Validate file extension
    if not audio.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a filename with extension (e.g., audio.mp3)",
        )

    ext: str = audio.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file
    audio_content = await audio.read()
    file_size = len(audio_content)

    # Check file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB",
        )

    logger.info(
        "DIARIZATION_UPLOAD_START",
        session_id=x_session_id,
        filename=audio.filename,
        size=file_size,
        lowprio_mode=USE_LOWPRIO_WORKER,
    )

    # Save audio file
    try:
        saved = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=ext,
            metadata={"original_filename": audio.filename, "purpose": "diarization"},
        )
    except Exception as e:
        logger.error("AUDIO_SAVE_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save audio: {str(e)}",
        ) from e

    # Path hardening: resolve absolute path
    from backend.audio_storage import AUDIO_STORAGE_DIR

    relative_path = saved["file_path"]
    abs_path = (AUDIO_STORAGE_DIR.parent / relative_path).resolve()

    # Assert file exists
    if not abs_path.is_file():
        logger.error(
            "AUDIO_FILE_NOT_FOUND_BEFORE_JOB",
            session_id=x_session_id,
            expected_path=str(abs_path),
            relative_path=relative_path,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio file not found after save: {relative_path}",
        )

    logger.info(
        "AUDIO_PATH_RESOLVED",
        session_id=x_session_id,
        absolute_path=str(abs_path),
        file_exists=abs_path.is_file(),
    )

    # Build configuration dict from optional parameters
    config_overrides: dict[str, Any] = {}
    if whisper_model is not None:
        config_overrides["whisper_model"] = whisper_model  # type: ignore
    if enable_llm_classification is not None:
        config_overrides["enable_llm_classification"] = enable_llm_classification  # type: ignore
    if chunk_size_sec is not None:
        config_overrides["chunk_size_sec"] = chunk_size_sec  # type: ignore
    if beam_size is not None:
        config_overrides["beam_size"] = beam_size  # type: ignore
    if vad_filter is not None:
        config_overrides["vad_filter"] = vad_filter  # type: ignore

    logger.info("CONFIG_OVERRIDES_RECEIVED", session_id=x_session_id, overrides=config_overrides)

    # Route to low-priority worker or legacy pipelines
    if USE_LOWPRIO_WORKER:
        # Use low-priority worker with CPU scheduler + HDF5
        job_id = create_lowprio_job(x_session_id, abs_path)
        logger.info(
            "LOWPRIO_JOB_CREATED", job_id=job_id, session_id=x_session_id, config=config_overrides
        )
    else:
        # Legacy: create in-memory job and use background task
        job_id = create_job(x_session_id, str(abs_path), file_size)

        if USE_V2_PIPELINE:
            background_tasks.add_task(
                _process_diarization_background_v2,
                job_id,
                abs_path,
                x_session_id,
                language,
                persist,
            )
        else:
            background_tasks.add_task(
                _process_diarization_background, job_id, abs_path, x_session_id, language, persist
            )

    return UploadResponse(
        job_id=job_id,
        session_id=x_session_id,
        status="pending",
        message=f"Diarization job created. Poll /api/diarization/jobs/{job_id} for status.",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of diarization job with chunks[] array.

    Low-priority mode:
    - Reads from HDF5 (storage/diarization.h5)
    - Returns incremental chunks as they complete
    - Frontend can poll at 1.5s intervals

    Legacy mode:
    - Reads from in-memory job store
    - No chunks[] array (empty)
    """
    # Try low-priority worker first
    if USE_LOWPRIO_WORKER:
        lowprio_status = get_lowprio_status(job_id)
        if lowprio_status:
            # Convert HDF5 chunks to API format
            chunks = [
                ChunkInfo(
                    chunk_idx=c["chunk_idx"],
                    start_time=c["start_time"],
                    end_time=c["end_time"],
                    text=c["text"],
                    speaker=c["speaker"],
                    temperature=c["temperature"],
                    rtf=c["rtf"],
                    timestamp=c["timestamp"],
                )
                for c in lowprio_status["chunks"]
            ]

            return JobStatusResponse(
                job_id=lowprio_status["job_id"],
                session_id=lowprio_status["session_id"],
                status=lowprio_status["status"],
                progress_pct=lowprio_status["progress_pct"],
                total_chunks=lowprio_status["total_chunks"],
                processed_chunks=lowprio_status["processed_chunks"],
                chunks=chunks,
                created_at=lowprio_status["created_at"],
                updated_at=lowprio_status["updated_at"],
                error=lowprio_status.get("error"),
            )

    # Fallback to legacy in-memory job store
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.job_id,
        session_id=job.session_id,
        status=job.status.value,
        progress_pct=job.progress_percent,
        total_chunks=job.total,
        processed_chunks=job.processed,
        chunks=[],  # Legacy mode: no incremental chunks
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error_message,
    )


@router.get("/result/{job_id}", response_model=DiarizationResultResponse)
async def get_diarization_result(job_id: str):
    """
    Get diarization result for completed job.

    Supports both legacy (in-memory) and low-priority (HDF5) workers.
    V2 improvement: Results are cached in job.result_data (no re-processing).
    """
    # Try low-priority worker first (HDF5)
    if USE_LOWPRIO_WORKER:
        lowprio_status = get_lowprio_status(job_id)
        if lowprio_status:
            # Low-prio job found in HDF5
            if lowprio_status["status"] != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Job not completed. Status: {lowprio_status['status']}",
                )

            # For low-prio jobs, reconstruct result from chunks
            logger.info(
                "RESULT_FROM_LOWPRIO_CHUNKS", job_id=job_id, chunks=len(lowprio_status["chunks"])
            )

            # Combine all chunks into segments
            segments: list[DiarizationSegmentResponse] = []
            for chunk in lowprio_status["chunks"]:
                segments.append(
                    DiarizationSegmentResponse(
                        start_time=chunk["start_time"],
                        end_time=chunk["end_time"],
                        speaker=chunk["speaker"],
                        text=chunk["text"],
                    )
                )

            # Compute total duration from last chunk
            total_duration: float = segments[-1].end_time if segments else 0.0

            return DiarizationResultResponse(
                session_id=lowprio_status["session_id"],
                audio_file_hash="",  # Not available in HDF5 chunks
                duration_sec=total_duration,
                language="es",  # Default (not stored in chunks)
                model_asr="faster-whisper",
                model_llm="none",  # Low-prio doesn't use LLM
                segments=segments,
                processing_time_sec=0.0,  # Not tracked per-job
                created_at=lowprio_status["created_at"],
            )

    # Fallback to legacy in-memory job store
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed. Status: {job.status.value}",
        )

    # Use cached result (V2) or re-process (V1 fallback)
    try:
        if job.result_data:
            # V2: Result cached in job, return immediately
            logger.info("RESULT_SERVED_FROM_CACHE", job_id=job_id)
            result_data = job.result_data

            return DiarizationResultResponse(
                session_id=result_data["session_id"],
                audio_file_hash=result_data["audio_file_hash"],
                duration_sec=result_data["duration_sec"],
                language=result_data["language"],
                model_asr=result_data["model_asr"],
                model_llm=result_data["model_llm"],
                segments=[
                    DiarizationSegmentResponse(
                        start_time=seg["start_time"],
                        end_time=seg["end_time"],
                        speaker=seg["speaker"],
                        text=seg["text"],
                    )
                    for seg in result_data["segments"]
                ],
                processing_time_sec=result_data["processing_time_sec"],
                created_at=result_data["created_at"],
            )

        # V1 fallback: Re-run diarization (expensive, but kept for compatibility)
        logger.warning("RESULT_NOT_CACHED_REPROCESSING", job_id=job_id)
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
                    text=seg.text,
                )
                for seg in result.segments
            ],
            processing_time_sec=result.processing_time_sec,
            created_at=result.created_at,
        )

    except Exception as e:
        logger.error("RESULT_LOAD_FAILED", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load result: {str(e)}",
        ) from e


@router.get("/export/{job_id}")
async def export_diarization_result(
    job_id: str, export_format: str = Query("json", regex="^(json|markdown)$", alias="format")
):
    """
    Export diarization result in specified format.

    Supports both legacy (in-memory) and low-priority (HDF5) workers.
    Uses cached results when available (no re-processing).
    """
    # Try low-priority worker first (HDF5)
    if USE_LOWPRIO_WORKER:
        lowprio_status = get_lowprio_status(job_id)
        if lowprio_status:
            # Low-prio job found in HDF5
            if lowprio_status["status"] != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Job not completed. Status: {lowprio_status['status']}",
                )

            # Reconstruct result from chunks (no re-processing)
            logger.info("EXPORT_FROM_LOWPRIO_CHUNKS", job_id=job_id, format=format)

            segments: list[dict] = []
            for chunk in lowprio_status["chunks"]:
                segments.append(
                    {
                        "start_time": chunk["start_time"],
                        "end_time": chunk["end_time"],
                        "speaker": chunk["speaker"],
                        "text": chunk["text"],
                    }
                )

            # Create simple export from chunks
            if export_format == "json":
                import json

                export_data: dict[str, Any] = {
                    "job_id": job_id,
                    "session_id": lowprio_status["session_id"],
                    "status": "completed",
                    "created_at": lowprio_status["created_at"],
                    "segments": segments,
                }
                content = json.dumps(export_data, indent=2)
                media_type = "application/json"
            else:  # markdown
                content = f"# Diarization Result - {job_id}\n\n"
                content += f"**Session:** {lowprio_status['session_id']}\n"
                content += f"**Created:** {lowprio_status['created_at']}\n\n"
                content += "## Segments\n\n"
                for seg in segments:
                    content += f"**[{seg['start_time']:.1f}s - {seg['end_time']:.1f}s] {seg['speaker']}:**\n"
                    content += f"{seg['text']}\n\n"
                media_type = "text/markdown"

            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename=diarization_{job_id}.{export_format}"
                },
            )

    # Fallback to legacy in-memory job store
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed. Status: {job.status.value}",
        )

    try:
        # Use cached result if available (no re-processing)
        result_data: Union[dict[str, Any], DiarizationResult]
        if job.result_data:
            logger.info("EXPORT_FROM_CACHE", job_id=job_id, format=export_format)
            result_data = job.result_data
        else:
            # Fallback: Re-process audio (should be rare)
            logger.warning("EXPORT_REPROCESSING_LEGACY", job_id=job_id)
            audio_path = Path(job.audio_file_path)
            result = diarize_audio(audio_path, job.session_id, language="es", persist=False)
            result_data = asdict(result) if hasattr(result, "__dataclass_fields__") else result  # type: ignore

        # Convert dict to DiarizationResult if needed
        if isinstance(result_data, DiarizationResult):
            diarization_result: DiarizationResult = result_data
        else:
            diarization_result = DiarizationResult(**result_data)

        export_content: str = export_diarization(diarization_result, export_format)

        if export_format == "json":
            return Response(
                content=export_content,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=diarization_{job_id}.json"},
            )
        else:  # markdown
            return Response(
                content=export_content,
                media_type="text/markdown",
                headers={"Content-Disposition": f"attachment; filename=diarization_{job_id}.md"},
            )

    except Exception as e:
        logger.error("EXPORT_FAILED", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {str(e)}"
        ) from e


@router.get("/jobs")
async def list_diarization_jobs(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
):
    """
    List diarization jobs from HDF5 storage (low-priority worker).
    Optionally filtered by session ID.
    """
    # Check if using low-priority worker
    if USE_LOWPRIO_WORKER:
        from backend.diarization_worker_lowprio import list_all_jobs as list_h5_jobs

        jobs_h5 = list_h5_jobs(session_id, limit)

        return {"jobs": jobs_h5, "count": len(jobs_h5)}

    # Fallback to legacy in-memory jobs
    jobs = list_jobs(session_id, limit)

    return {
        "jobs": [
            {
                "job_id": j.job_id,
                "session_id": j.session_id,
                "status": j.status.value,
                "progress_percent": j.progress_percent,
                "created_at": j.created_at,
                "completed_at": j.completed_at,
            }
            for j in jobs
        ],
        "count": len(jobs),
    }


@router.get("/health")
async def diarization_health():
    """
    Health check for diarization service.

    Returns:
        - status: operational | degraded | down
        - whisper: bool (ASR availability) - ALSO returns as whisper_available for frontend compatibility
        - llm: bool (Ollama availability) - ALSO returns as ollama_available for frontend compatibility
        - enrichment_enabled: bool (FI_ENRICHMENT status)
        - message: human-readable status
    """
    from backend.diarization_service import (
        ENABLE_LLM_CLASSIFICATION,
        FI_ENRICHMENT,
        check_ollama_available,
    )
    from backend.whisper_service import is_whisper_available

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
        # Legacy field names (for backward compatibility)
        "whisper": whisper_ok,
        "llm": llm_ok,
        # Frontend field names (FI-UI-FEAT-207)
        "whisper_available": whisper_ok,
        "ollama_available": llm_ok,
        # Metadata
        "enrichment_enabled": enrichment_enabled,
        "message": f"Diarization service {status_text}",
    }


@router.post("/jobs/{job_id}/restart")
async def restart_job(job_id: str):
    """
    Restart a stuck or failed diarization job.

    Creates a new job with the same audio file and session ID.
    Returns new job_id.
    """
    if USE_LOWPRIO_WORKER:
        # Get original job details from HDF5
        from backend.diarization_worker_lowprio import (
            create_diarization_job as create_lowprio_job,
        )
        from backend.diarization_worker_lowprio import (
            get_job_status as get_lowprio_status,
        )

        original_job = get_lowprio_status(job_id)
        if not original_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found in HDF5. This may be an old job created before low-priority worker was enabled.",
            )

        # Get audio path from HDF5 metadata
        import h5py  # type: ignore

        h5_path = Path("storage/diarization.h5")

        try:
            with h5py.File(h5_path, "r") as f:
                job_group = f[f"jobs/{job_id}"]
                audio_path_str = job_group.attrs.get("audio_path", "")  # type: ignore

                if not audio_path_str:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Audio path not found in job metadata",
                    )

                audio_path = Path(audio_path_str)

                if not audio_path.is_file():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Audio file no longer exists: {audio_path}",
                    )

                # Create new job
                new_job_id = create_lowprio_job(original_job["session_id"], audio_path)

                logger.info("JOB_RESTARTED", old_job_id=job_id, new_job_id=new_job_id)

                return {
                    "message": "Job restarted successfully",
                    "old_job_id": job_id,
                    "new_job_id": new_job_id,
                    "status": "pending",
                }

        except Exception as e:
            logger.error("JOB_RESTART_FAILED", job_id=job_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to restart job: {str(e)}",
            ) from e

    # Legacy mode: restart from in-memory job
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    # Create new job with same audio
    audio_path = Path(job.audio_file_path)
    new_job_id = create_job(job.session_id, str(audio_path), audio_path.stat().st_size)

    logger.info("JOB_RESTARTED_LEGACY", old_job_id=job_id, new_job_id=new_job_id)

    return {
        "message": "Job restarted successfully",
        "old_job_id": job_id,
        "new_job_id": new_job_id,
        "status": "pending",
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running diarization job.

    Marks job as cancelled in HDF5 or in-memory store.
    """
    if USE_LOWPRIO_WORKER:
        # Cancel job in HDF5
        import h5py  # type: ignore

        h5_path = Path("storage/diarization.h5")

        try:
            with h5py.File(h5_path, "a") as f:
                if f"jobs/{job_id}" not in f:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
                    )

                job_group = f[f"jobs/{job_id}"]
                job_group.attrs["status"] = "cancelled"  # type: ignore
                job_group.attrs["updated_at"] = str(asyncio.get_event_loop().time())  # type: ignore

                logger.info("JOB_CANCELLED", job_id=job_id)

                return {
                    "message": "Job cancelled successfully",
                    "job_id": job_id,
                    "status": "cancelled",
                }

        except Exception as e:
            logger.error("JOB_CANCEL_FAILED", job_id=job_id, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel job: {str(e)}",
            ) from e

    # Legacy mode: cancel in-memory job
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    update_job_status(job_id, JobStatus.FAILED, error="Cancelled by user")

    logger.info("JOB_CANCELLED_LEGACY", job_id=job_id)

    return {"message": "Job cancelled successfully", "job_id": job_id, "status": "cancelled"}


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """
    Get logs for a specific diarization job.

    Returns job metadata + chunk processing history from HDF5.
    """
    if USE_LOWPRIO_WORKER:
        from backend.diarization_worker_lowprio import (
            get_job_status as get_lowprio_status,
        )

        job_status = get_lowprio_status(job_id)
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
            )

        # Return full job state as "logs"
        return {
            "job_id": job_id,
            "session_id": job_status["session_id"],
            "status": job_status["status"],
            "progress_pct": job_status["progress_pct"],
            "processed_chunks": job_status["processed_chunks"],
            "total_chunks": job_status["total_chunks"],
            "created_at": job_status["created_at"],
            "updated_at": job_status["updated_at"],
            "error": job_status.get("error"),
            "chunks": job_status["chunks"],
            "message": f"Retrieved {len(job_status['chunks'])} chunks from HDF5",
        }

    # Legacy mode: return in-memory job state
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    return {
        "job_id": job.job_id,
        "session_id": job.session_id,
        "status": job.status.value,
        "progress_percent": job.progress_percent,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "error": job.error_message,
        "message": "Legacy in-memory job (no chunk logs available)",
    }
