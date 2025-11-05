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

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

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

from backend.storage.audio_storage import save_audio_file
from backend.container import get_container
try:
    from backend.services.diarization_jobs import JobStatus, create_job, update_job_status
except ImportError:
    # Fallback for compatibility
    from backend.diarization_jobs import JobStatus, create_job, update_job_status
try:
    from backend.services.diarization_service import diarize_audio
except ImportError:
    from backend.diarization_service import diarize_audio
try:
    from backend.services.diarization_service_v2 import diarize_audio_parallel
except ImportError:
    from backend.diarization_service_v2 import diarize_audio_parallel
# Lazy import for low-priority worker
def create_lowprio_job(session_id, audio_path):
    """Lazy wrapper for low-priority job creation."""
    try:
        from backend.jobs.diarization_worker_lowprio import (
            create_diarization_job,
        )
        return create_diarization_job(session_id, audio_path)
    except (ImportError, AttributeError):
        raise RuntimeError("Low-priority worker not available")
from backend.logger import get_logger
from backend.schemas import StatusCode, error_response, success_response
from backend.services.soap_generation_service import SOAPGenerationService

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


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
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

    **Clean Code Architecture:**
    - DiarizationService handles validation and job creation
    - Audio file storage managed by CorpusService
    - AuditService logs all uploads
    - Uses DI container for dependency injection

    Low-priority mode (DIARIZATION_LOWPRIO=true):
    - Uses CPU scheduler (only runs when CPU idle ≥50%)
    - Saves chunks incrementally to HDF5
    - Does NOT block main thread

    Returns job_id for tracking progress.
    """
    # Get services from DI container (clean code pattern) - must be outside try/except
    diarization_service = get_container().get_diarization_service()
    audit_service = get_container().get_audit_service()

    try:
        # Validate required headers and filename
        if not x_session_id:
            raise ValueError("X-Session-ID header is required")
        if not audio.filename:
            raise ValueError("Audio filename is required")

        # Read audio file
        audio_content = await audio.read()

        # Validate and create job via service layer
        # Service handles: filename validation, extension check, size validation, session validation
        job_metadata = diarization_service.create_diarization_job(
            session_id=x_session_id,
            audio_filename=audio.filename,
            audio_content=audio_content,
            language=language,
            persist=persist,
            whisper_model=whisper_model,
        )

        job_id = job_metadata["job_id"]

        # Log the upload action via audit service
        audit_service.log_action(
            action="audio_uploaded_for_diarization",
            user_id="system",  # Could get from session/JWT token
            resource=f"job:{job_id}",
            result="success",
            details={
                "filename": audio.filename,
                "language": language,
                "session_id": x_session_id,
                "persist": persist,
            },
        )

        logger.info(
            "DIARIZATION_UPLOAD_START",
            session_id=x_session_id,
            job_id=job_id,
            filename=audio.filename,
            size=len(audio_content),
            lowprio_mode=USE_LOWPRIO_WORKER,
        )

        # Still need to save audio file for low-priority worker (for now)
        # TODO: Move audio storage to DiarizationService in future iteration
        try:
            saved = save_audio_file(
                session_id=x_session_id,
                audio_content=audio_content,
                file_extension=audio.filename.rsplit(".", 1)[-1].lower()
                if audio.filename
                else "mp3",
                metadata={"original_filename": audio.filename, "purpose": "diarization"},
            )
        except Exception as e:
            logger.error("AUDIO_SAVE_FAILED", job_id=job_id, error=str(e))
            diarization_service.fail_job(job_id, f"Failed to save audio: {str(e)}")
            audit_service.log_action(
                action="audio_upload_failed",
                user_id="system",
                resource=f"job:{job_id}",
                result="failed",
                details={"error": str(e)},
            )
            return error_response(
                "Failed to save audio file", code=500, status=StatusCode.INTERNAL_ERROR
            )

        # Path hardening: resolve absolute path
        from backend.storage.audio_storage import AUDIO_STORAGE_DIR

        relative_path = saved["file_path"]
        abs_path = (AUDIO_STORAGE_DIR.parent / relative_path).resolve()

        # Assert file exists
        if not abs_path.is_file():
            logger.error(
                "AUDIO_FILE_NOT_FOUND_BEFORE_JOB",
                session_id=x_session_id,
                job_id=job_id,
                expected_path=str(abs_path),
                relative_path=relative_path,
            )
            diarization_service.fail_job(job_id, f"Audio file not found: {relative_path}")
            return error_response(
                f"Audio file not found after save: {relative_path}",
                code=500,
                status=StatusCode.INTERNAL_ERROR,
            )

        logger.info(
            "AUDIO_PATH_RESOLVED",
            session_id=x_session_id,
            job_id=job_id,
            absolute_path=str(abs_path),
            file_exists=abs_path.is_file(),
        )

        # Build configuration dict from optional parameters
        config_overrides: dict[str, Any] = {}
        if whisper_model is not None:
            config_overrides["whisper_model"] = whisper_model
        if enable_llm_classification is not None:
            config_overrides["enable_llm_classification"] = enable_llm_classification
        if chunk_size_sec is not None:
            config_overrides["chunk_size_sec"] = chunk_size_sec
        if beam_size is not None:
            config_overrides["beam_size"] = beam_size
        if vad_filter is not None:
            config_overrides["vad_filter"] = vad_filter

        logger.info(
            "CONFIG_OVERRIDES_RECEIVED",
            session_id=x_session_id,
            job_id=job_id,
            overrides=config_overrides,
        )

        # Route to low-priority worker or legacy pipelines
        if USE_LOWPRIO_WORKER:
            # Use low-priority worker with CPU scheduler + HDF5
            job_id = create_lowprio_job(x_session_id, abs_path)  # type: ignore[call-arg]
            logger.info(
                "LOWPRIO_JOB_CREATED",
                job_id=job_id,
                session_id=x_session_id,
                config=config_overrides,
            )
        else:
            # Legacy: create in-memory job and use background task
            job_id = create_job(x_session_id, str(abs_path), len(audio_content))  # type: ignore[call-arg]

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
                    _process_diarization_background,
                    job_id,
                    abs_path,
                    x_session_id,
                    language,
                    persist,
                )

        # Return standardized success response
        return success_response(
            {
                "job_id": job_id,
                "session_id": x_session_id,
                "status": "pending",
            },
            message=f"Diarization job created. Poll /api/diarization/jobs/{job_id} for status.",
            code=202,
        )

    except ValueError as e:
        # Validation error (bad input)
        logger.warning("DIARIZATION_VALIDATION_FAILED")
        audit_service.log_action(
            action="diarization_upload_validation_failed",
            user_id="system",
            resource="upload",
            result="failed",
            details={"error": str(e), "session_id": x_session_id},
        )
        return error_response(str(e), code=400, status=StatusCode.VALIDATION_ERROR)

    except OSError as e:
        # Storage error
        logger.error("DIARIZATION_STORAGE_FAILED")
        audit_service.log_action(
            action="diarization_upload_storage_failed",
            user_id="system",
            resource="upload",
            result="failed",
            details={"error": str(e), "session_id": x_session_id},
        )
        return error_response(
            "Failed to store audio file", code=500, status=StatusCode.INTERNAL_ERROR
        )

    except Exception as e:
        # Unexpected error
        import traceback

        error_trace = traceback.format_exc()
        logger.error("DIARIZATION_UPLOAD_FAILED", error=str(e), traceback=error_trace)
        audit_service.log_action(
            action="diarization_upload_failed",
            user_id="system",
            resource="upload",
            result="failed",
            details={"error": str(e), "session_id": x_session_id},
        )
        return error_response("Internal server error", code=500, status=StatusCode.INTERNAL_ERROR)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get status of diarization job with chunks[] array.

    **Clean Code Architecture:**
    - DiarizationJobService handles status retrieval from both HDF5 and in-memory
    - AuditService logs retrieval
    - Uses DI container for dependency injection
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service layer
        status_dict = job_service.get_job_status(job_id)

        if not status_dict:
            logger.warning(f"JOB_NOT_FOUND: job_id={job_id}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Log audit trail
        audit_service.log_action(
            action="job_status_retrieved",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"status": status_dict.get("status")},
        )

        logger.info(f"JOB_STATUS_RETRIEVED: job_id={job_id}, status={status_dict['status']}")

        # Convert chunks to response model
        chunks = [
            ChunkInfo(
                chunk_idx=c["chunk_idx"],
                start_time=c["start_time"],
                end_time=c["end_time"],
                text=c["text"],
                speaker=c["speaker"],
                temperature=c.get("temperature", 0.0),
                rtf=c.get("rtf", 0.0),
                timestamp=c.get("timestamp", ""),
            )
            for c in status_dict.get("chunks", [])
        ]

        return JobStatusResponse(
            job_id=status_dict["job_id"],
            session_id=status_dict["session_id"],
            status=status_dict["status"],
            progress_pct=status_dict.get("progress_pct", 0),
            total_chunks=status_dict.get("total_chunks", 0),
            processed_chunks=status_dict.get("processed_chunks", 0),
            chunks=chunks,
            created_at=status_dict["created_at"],
            updated_at=status_dict["updated_at"],
            error=status_dict.get("error"),
        )

    except ValueError as e:
        logger.warning(f"JOB_STATUS_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"JOB_STATUS_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status") from e


@router.get("/result/{job_id}", response_model=DiarizationResultResponse)
async def get_diarization_result(job_id: str):
    """
    Get diarization result for completed job.

    **Clean Code Architecture:**
    - DiarizationJobService handles result reconstruction and caching
    - Supports both HDF5 (low-prio) and in-memory (legacy) job stores
    - AuditService logs retrieval
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service layer
        result_dict = job_service.get_diarization_result(job_id)

        if not result_dict:
            logger.warning(f"DIARIZATION_RESULT_NOT_FOUND: job_id={job_id}")
            raise HTTPException(status_code=404, detail=f"Result not found for job {job_id}")

        # Log audit trail
        audit_service.log_action(
            action="diarization_result_retrieved",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"segments": len(result_dict.get("segments", []))},
        )

        logger.info(f"DIARIZATION_RESULT_RETRIEVED: job_id={job_id}")

        # Build response
        segments = [
            DiarizationSegmentResponse(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                speaker=seg["speaker"],
                text=seg["text"],
            )
            for seg in result_dict.get("segments", [])
        ]

        return DiarizationResultResponse(
            session_id=result_dict["session_id"],
            audio_file_hash=result_dict.get("audio_file_hash", ""),
            duration_sec=result_dict["duration_sec"],
            language=result_dict.get("language", "es"),
            model_asr=result_dict.get("model_asr", "faster-whisper"),
            model_llm=result_dict.get("model_llm", "none"),
            segments=segments,
            processing_time_sec=result_dict.get("processing_time_sec", 0.0),
            created_at=result_dict["created_at"],
        )

    except ValueError as e:
        logger.warning(f"DIARIZATION_RESULT_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DIARIZATION_RESULT_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve result") from e


@router.get("/export/{job_id}")
async def export_diarization_result(
    job_id: str,
    export_format: str = Query("json", regex="^(json|markdown|vtt|srt|csv)$", alias="format"),
):
    """
    Export diarization result in specified format.

    **Clean Code Architecture:**
    - DiarizationJobService handles export formatting
    - Supports: json, markdown, vtt, srt, csv
    - AuditService logs export
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Validate format
        valid_formats = {"json", "markdown", "vtt", "srt", "csv"}
        if export_format not in valid_formats:
            raise ValueError(f"Invalid format: {export_format}")

        # Delegate to service layer
        exported_content = job_service.export_result(job_id, export_format)

        if not exported_content:
            raise HTTPException(status_code=404, detail=f"Result not found for job {job_id}")

        # Log audit trail
        audit_service.log_action(
            action="diarization_exported",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"format": export_format, "size": len(exported_content)},
        )

        logger.info(f"DIARIZATION_EXPORTED: job_id={job_id}, format={export_format}")

        # Return appropriate content type
        content_types = {
            "json": "application/json",
            "markdown": "text/markdown",
            "vtt": "text/vtt",
            "srt": "text/plain",
            "csv": "text/csv",
        }

        filename = f"diarization_{job_id}.{export_format if export_format != 'markdown' else 'md'}"

        return Response(
            content=exported_content,
            media_type=content_types.get(export_format, "text/plain"),
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ValueError as e:
        logger.warning(f"DIARIZATION_EXPORT_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"DIARIZATION_EXPORT_FAILED: job_id={job_id}, format={export_format}, error={str(e)}"
        )
        raise HTTPException(status_code=500, detail="Failed to export result") from e


@router.get("/jobs")
async def list_diarization_jobs(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
):
    """
    List diarization jobs with optional filtering.

    **Clean Code Architecture:**
    - DiarizationJobService handles job listing and filtering
    - AuditService logs list operation
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service layer
        jobs = job_service.list_jobs(limit=limit, session_id=session_id)

        # Log audit trail
        audit_service.log_action(
            action="diarization_jobs_listed",
            user_id="system",
            resource="diarization_jobs",
            result="success",
            details={"count": len(jobs), "limit": limit},
        )

        logger.info(f"DIARIZATION_JOBS_LISTED: count={len(jobs)}, limit={limit}")

        return success_response(
            [
                {
                    "job_id": j["job_id"],
                    "session_id": j["session_id"],
                    "status": j.get("status"),
                    "progress_pct": j.get("progress_pct", 0),
                    "processed_chunks": j.get("processed_chunks", 0),
                    "total_chunks": j.get("total_chunks", 0),
                    "created_at": j.get("created_at"),
                    "updated_at": j.get("updated_at"),
                    "error": j.get("error"),
                }
                for j in jobs
            ],
            message=f"Found {len(jobs)} jobs",
        )

    except Exception as e:
        logger.error(f"DIARIZATION_JOBS_LIST_FAILED: error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list jobs") from e


@router.post("/soap/{job_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def generate_soap_for_job(job_id: str):
    """
    Generate SOAP note from diarization job transcription.

    **ConversationCapture MVP (Level 1):**
    - Reads transcription chunks from HDF5 diarization storage
    - Calls Ollama LLM to extract SOAP sections
    - Returns structured SOAP note (Subjetivo-Objetivo-Análisis-Plan)

    Args:
        job_id: Diarization job ID

    Returns:
        SOAP extraction result with medical data

    Raises:
        HTTPException: 404 if job not found, 500 if generation fails
    """
    try:
        # Initialize SOAP generation service
        soap_service = SOAPGenerationService()

        # Get transcription from HDF5 and extract SOAP with Ollama
        transcription = soap_service._read_transcription_from_h5(job_id)
        if not transcription:
            raise HTTPException(status_code=404, detail=f"No transcription found for job {job_id}")

        soap_data = soap_service._extract_soap_with_ollama(transcription)

        # Log audit trail
        audit_service = get_container().get_audit_service()
        audit_service.log_action(
            action="soap_generated",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={
                "model": "ollama_mistral_mvp",
                "extraction_success": bool(soap_data.get("subjetivo")),
            },
        )

        logger.info(
            "SOAP_GENERATION_SUCCESS",
            job_id=job_id,
            soap_data_keys=list(soap_data.keys()),
        )

        # Return extracted SOAP data
        return {
            "job_id": job_id,
            "soap_extraction": soap_data,
            "status": "success",
            "model": "ollama_mistral_mvp",
        }

    except ValueError as e:
        logger.warning(f"SOAP_GENERATION_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"SOAP_GENERATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate SOAP note") from e


@router.get("/health")
async def diarization_health():
    """
    Check diarization service health.

    **Clean Code Architecture:**
    - DiarizationService handles health check logic
    - Reports on Whisper, FFmpeg, and active jobs
    """
    try:
        # Get services from DI container
        diarization_service = get_container().get_diarization_service()

        # Delegate to service layer
        health_details = diarization_service.health_check()

        logger.info("DIARIZATION_HEALTH_CHECKED", status=health_details["status"])

        # Transform response for frontend compatibility
        # Frontend expects top-level whisper_available and ollama_available fields
        whisper_available = (
            health_details.get("components", {}).get("whisper", {}).get("available", False)
        )

        frontend_response = {
            "status": health_details["status"],
            "whisper_available": whisper_available,
            "ollama_available": False,  # Will be checked by other endpoints
            "components": health_details.get("components", {}),
            "active_jobs": health_details.get("active_jobs", 0),
        }

        # Return appropriate status code
        status_code = 200 if health_details["status"] == "healthy" else 503

        return Response(
            content=json.dumps(frontend_response),
            media_type="application/json",
            status_code=status_code,
        )

    except Exception as e:
        logger.error(f"DIARIZATION_HEALTH_CHECK_FAILED: error={str(e)}")
        return Response(
            content=json.dumps({"status": "unhealthy", "error": str(e)}),
            media_type="application/json",
            status_code=503,
        )


@router.post("/jobs/{job_id}/restart")
async def restart_job(job_id: str):
    """
    Restart diarization job.

    **Clean Code Architecture:**
    - DiarizationJobService handles job restart logic
    - AuditService logs restart action
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service layer
        updated_status = job_service.restart_job(job_id)

        # Log audit trail
        audit_service.log_action(
            action="diarization_job_restarted",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"new_status": updated_status.get("status")},
        )

        logger.info(f"DIARIZATION_JOB_RESTARTED: job_id={job_id}")

        return success_response(updated_status, message=f"Job {job_id} restarted", code=200)

    except ValueError as e:
        logger.warning(f"JOB_RESTART_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"JOB_RESTART_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to restart job") from e


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel diarization job.

    **Clean Code Architecture:**
    - DiarizationJobService handles job cancellation
    - AuditService logs cancel action
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service layer
        updated_status = job_service.cancel_job(job_id)

        # Log audit trail
        audit_service.log_action(
            action="diarization_job_cancelled",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"new_status": updated_status.get("status")},
        )

        logger.info(f"DIARIZATION_JOB_CANCELLED: job_id={job_id}")

        return success_response(updated_status, message=f"Job {job_id} cancelled", code=200)

    except ValueError as e:
        logger.warning(f"JOB_CANCEL_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"JOB_CANCEL_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel job") from e


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """
    Get processing logs for a diarization job.

    **Clean Code Architecture:**
    - DiarizationJobService handles log retrieval
    - AuditService logs access
    """
    try:
        # Get services from DI container
        job_service = get_container().get_diarization_job_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service layer
        logs = job_service.get_job_logs(job_id)

        if logs is None:
            logger.warning(f"JOB_LOGS_NOT_FOUND: job_id={job_id}")
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Log audit trail
        audit_service.log_action(
            action="diarization_logs_retrieved",
            user_id="system",
            resource=f"diarization_job:{job_id}",
            result="success",
            details={"log_entries": len(logs) if logs else 0},
        )

        logger.info(
            f"DIARIZATION_LOGS_RETRIEVED: job_id={job_id}, count={len(logs) if logs else 0}"
        )

        return success_response(
            logs or [], message=f"Retrieved {len(logs) if logs else 0} log entries", code=200
        )

    except ValueError as e:
        logger.warning(f"DIARIZATION_LOGS_VALIDATION_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"DIARIZATION_LOGS_FAILED: job_id={job_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs") from e
