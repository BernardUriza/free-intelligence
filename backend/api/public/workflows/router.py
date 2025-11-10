"""Aurity App Orchestrator - Public API workflows.

Card: FI-BACKEND-ARCH-001

This module provides orchestrator endpoints for the Aurity application.
Orchestrators coordinate multiple internal services to provide unified,
high-level operations for frontend clients.

Architecture:
- Only orchestrators exposed via CORS to public clients
- Calls internal atomic resources (/internal/*)
- No business logic, only coordination
- Audit trail for all operations

Endpoints:
- POST /api/workflows/aurity/consult - Audio → Transcription → SOAP (end-to-end)
- GET /api/workflows/aurity/consult/{job_id} - Get consult status

File: backend/api/workflows/router.py
Created: 2025-11-08 (orchestrator pattern implementation)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])

# Dev-only: load .env.local if exists; in prod use real process vars
try:
    from dotenv import load_dotenv

    load_dotenv(".env.local")
except Exception:
    pass

# Environment configuration (absolute path + mkdir)
AUDIO_DIR = Path(os.getenv("AURITY_AUDIO_ROOT", "storage/audio")).resolve()
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_BIN", "ffprobe")
ENABLE_GRAFT = os.getenv("AURITY_ENABLE_WEBM_GRAFT", "false").lower() in {"1", "true", "yes"}

# WebM EBML Cluster ID for header extraction
EBML_CLUSTER_ID = b"\x1F\x43\xB6\x75"
_header_cache: dict[str, bytes] = {}

# Global semaphore to limit concurrent SOAP generation (max 1 at a time)
_soap_worker_semaphore = threading.Semaphore(1)


def _atomic_write(src_file: UploadFile, dst_path: Path) -> Path:
    """
    Atomically write uploaded file to destination with fsync.

    **Args:**
    - src_file: FastAPI UploadFile
    - dst_path: Target path

    **Returns:**
    - Path to written file

    **Guarantees:**
    - Atomic rename (no partial writes visible)
    - fsync before rename (data persisted to disk)
    - Parent directory created if missing
    """
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dst_path.parent, delete=False) as tmp:
        shutil.copyfileobj(src_file.file, tmp)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(dst_path)  # Atomic rename
    return dst_path


def _probe_ok(path: Path) -> bool:
    """
    Validate audio file with ffprobe.

    **Args:**
    - path: Path to audio file

    **Returns:**
    - True if valid audio stream detected, False otherwise

    **Guards:**
    - Detects invalid/corrupted containers
    - Prevents ffmpeg decode failures downstream
    """
    try:
        subprocess.run(
            [FFPROBE, "-v", "error", "-show_streams", "-select_streams", "a:0", path.as_posix()],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            timeout=5,
        )
        return True
    except Exception:
        return False


def _to_wav(src: Path, dst: Path) -> None:
    """
    Convert audio to WAV with conservative flags for fragmented WebM/Opus.

    **Args:**
    - src: Source audio file (WebM, MP3, etc.)
    - dst: Destination WAV file (16kHz mono)

    **Flags:**
    - genpts: Generate presentation timestamps
    - igndts: Ignore decode timestamps (for fragmented streams)
    - ac 1: Mono output
    - ar 16000: 16kHz sample rate (Whisper optimal)

    **Raises:**
    - subprocess.CalledProcessError if conversion fails
    """
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-fflags",
        "+genpts+igndts",
        "-i",
        src.as_posix(),
        "-ac",
        "1",
        "-ar",
        "16000",
        dst.as_posix(),
    ]
    subprocess.run(cmd, check=True, timeout=30)


def _extract_header_bytes(webm_bytes: bytes) -> bytes:
    """
    Extract WebM EBML header (everything before first Cluster).

    **Args:**
    - webm_bytes: Raw WebM file bytes

    **Returns:**
    - Header bytes (EBML + Segment Info + Tracks)

    **Notes:**
    - Searches for EBML Cluster ID (0x1F43B675)
    - If no cluster found, returns first 4KB (conservative)
    """
    idx = webm_bytes.find(EBML_CLUSTER_ID)
    if idx == -1:
        return webm_bytes[: min(len(webm_bytes), 4096)]
    return webm_bytes[:idx]


def _ensure_session_header(sess_dir: Path, chunk0_path: Path) -> bytes:
    """
    Extract and cache session header from chunk 0.

    **Args:**
    - sess_dir: Session directory
    - chunk0_path: Path to first chunk (0.webm)

    **Returns:**
    - Header bytes

    **Side Effects:**
    - Caches header in memory (_header_cache)
    - Persists header to sess_dir/_header.bin for inspection
    """
    key = sess_dir.as_posix()
    hb = _header_cache.get(key)
    if hb is not None:
        return hb
    data = chunk0_path.read_bytes()
    hb = _extract_header_bytes(data)
    _header_cache[key] = hb
    (sess_dir / "_header.bin").write_bytes(hb)
    logger.info("HEADER_EXTRACTED", session=key, header_size=len(hb))
    return hb


def _resolve_ext(mime: str) -> str:
    """
    Resolve file extension from MIME type.

    **Args:**
    - mime: MIME type string (e.g., "audio/webm;codecs=opus")

    **Returns:**
    - File extension (.webm, .mp4, .wav, .bin)
    """
    m = mime.split(";")[0].strip().lower()
    if m == "audio/webm":
        return ".webm"
    if m in {"audio/mp4", "audio/mp4a-latm"}:
        return ".mp4"
    if m in {"audio/wav", "audio/wave", "audio/x-wav"}:
        return ".wav"
    return ".bin"


def _is_ebml(path: Path) -> bool:
    """
    Check if file has valid EBML header (0x1A45DFA3).

    **Args:**
    - path: Path to file

    **Returns:**
    - True if file starts with EBML magic number
    """
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"\x1A\x45\xDF\xA3"
    except Exception:
        return False


def _maybe_graft_header(sess_dir: Path, chunk_number: int, raw_path: Path) -> Path:
    """
    Graft WebM header to chunk if needed (chunks > 0).

    **Args:**
    - sess_dir: Session directory
    - chunk_number: Sequential chunk number
    - raw_path: Path to raw chunk file

    **Returns:**
    - Path to grafted file (or raw_path if chunk 0)

    **Logic:**
    - Chunk 0: Return as-is (has header)
    - Chunk N>0: Prepend header from chunk 0
    - If no header available: Return raw_path (frontend should have grafted)
    - Search for chunk 0 with extensions: .webm, .mp4, .ogg

    **Output:**
    - Creates {chunk_number}.grafted.webm if grafting applied
    """
    # Only WebM chunks and only after first chunk
    if raw_path.suffix != ".webm" or chunk_number == 0:
        return raw_path

    # Find chunk 0 with any supported extension
    c0 = None
    for ext in (".webm", ".mp4", ".ogg"):
        p = sess_dir / f"0{ext}"
        if p.exists():
            c0 = p
            break

    if not c0:
        logger.warning(
            "HEADER_MISSING_CHUNK0_NOT_FOUND", session=sess_dir.as_posix(), chunk=chunk_number
        )
        return raw_path

    # Extract and cache header from chunk 0
    hb = _ensure_session_header(sess_dir, c0)

    # Create grafted file: header + chunk
    grafted = raw_path.with_suffix(".grafted.webm")
    with open(grafted, "wb") as g, open(raw_path, "rb") as r:
        g.write(hb)
        g.write(r.read())

    logger.info("HEADER_GRAFTED", chunk=chunk_number, grafted_size=grafted.stat().st_size)
    return grafted


class ConsultStartResponse(BaseModel):
    """Response for starting a consultation workflow."""

    job_id: str = Field(..., description="Unique job identifier")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="Current status (pending, in_progress, completed)")
    message: str = Field(..., description="Human-readable status message")


class ConsultStatusResponse(BaseModel):
    """Response for checking consultation status."""

    job_id: str
    session_id: str
    status: str
    progress_pct: int
    stages: dict[str, str] = Field(
        ...,
        description="Status of each stage: upload, transcribe, diarize, soap",
    )
    soap_note: Optional[dict] = Field(None, description="SOAP note if completed")
    result_data: Optional[dict] = Field(
        None, description="Full result data (transcription + diarization)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class StreamChunkResponse(BaseModel):
    """Response for real-time audio chunk processing (AUR-PROMPT-4.2)."""

    chunk_id: str = Field(..., description="Unique chunk identifier (or job_id if queued)")
    session_id: str = Field(..., description="Session identifier")
    chunk_number: int = Field(..., description="Sequential chunk number")
    transcription: Optional[str] = Field(
        None, description="Partial transcription text (null if queued)"
    )
    speaker: Optional[str] = Field(None, description="Detected speaker (if diarization enabled)")
    timestamp_start: float = Field(..., description="Start time in seconds")
    timestamp_end: float = Field(..., description="End time in seconds")
    status: str = Field(..., description="Chunk status: queued, processing, completed, failed")
    error: Optional[str] = Field(None, description="Error message if failed")
    queued: bool = Field(default=False, description="True if job queued (async processing)")
    job_id: Optional[str] = Field(None, description="Celery job ID for polling (if queued=True)")


@router.post("/consult", response_model=ConsultStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_consult_workflow(
    audio: UploadFile = File(..., description="Audio file (webm, wav, mp3, etc.)"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> ConsultStartResponse:
    """
    Start end-to-end consultation workflow: Audio → Transcription → SOAP.

    **Orchestration Flow:**
    1. Upload audio to storage (calls internal files service)
    2. Start diarization job (calls internal diarization service)
    3. Background: Transcription + speaker separation
    4. Background: SOAP extraction via Ollama
    5. Return job_id for status polling

    **Args:**
    - audio: Audio file (max 100MB, formats: webm, wav, mp3, m4a, ogg)
    - X-Session-ID: Session identifier (header)

    **Returns:**
    - job_id: Unique identifier for polling status
    - session_id: Session identifier
    - status: Current workflow status
    - message: Human-readable status

    **Errors:**
    - 400: Invalid session_id or file format
    - 413: File too large
    - 500: Workflow initiation failed

    **Notes:**
    - This is an orchestrator: coordinates internal services
    - Does NOT contain business logic (delegates to services)
    - Async processing: returns immediately with job_id
    - Use GET /workflows/aurity/consult/{job_id} to check progress
    """
    # Validate session ID
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Session-ID",
        )

    try:
        # Get services from DI container
        diarization_service = get_container().get_diarization_service()
        audit_service = get_container().get_audit_service()

        # Read audio content
        audio_content = await audio.read()
        audio_size = len(audio_content)

        # Orchestration Step 1: Save audio file to temporary storage
        import os
        import tempfile

        temp_dir = os.path.join(tempfile.gettempdir(), "fi_audio")
        os.makedirs(temp_dir, exist_ok=True)

        # Create unique filename with session_id
        audio_filename = audio.filename or "audio.webm"
        audio_path = os.path.join(temp_dir, f"{x_session_id}_{audio_filename}")

        # Save audio file
        with open(audio_path, "wb") as f:
            f.write(audio_content)

        logger.info(
            "WORKFLOW_AUDIO_SAVED",
            session_id=x_session_id,
            path=audio_path,
            size=audio_size,
        )

        # Orchestration Step 2: Create diarization job
        # This creates a job entry in the job tracker (in-memory or HDF5)
        try:
            job_id = diarization_service.create_job(
                session_id=x_session_id,
                audio_file_path=audio_path,
                audio_file_size=audio_size,
            )
            logger.info("JOB_CREATED_SUCCESS", job_id=job_id)
        except Exception as e:
            logger.error("JOB_CREATION_FAILED", error=str(e), error_type=type(e).__name__)
            raise

        # Orchestration Step 3: Trigger background processing via Celery
        # Primary: Celery distributed task queue (production-ready)
        # Fallback: threading.Thread (development mode if Celery unavailable)
        try:
            from backend.workers.tasks import process_diarization_job

            # Queue job for async processing with Celery
            task = process_diarization_job.delay(job_id)

            logger.info(
                "WORKFLOW_WORKER_QUEUED",
                job_id=job_id,
                task_id=task.id,
                backend="celery",
            )
        except ImportError:
            # Fallback to threading if Celery not available (dev mode)
            logger.warning("CELERY_UNAVAILABLE_FALLBACK_THREADING", job_id=job_id)

            import threading

            from backend.services.diarization.worker import process_job
            from backend.services.transcription.service import TranscriptionService

            def process_job_async(job_id_to_process: str) -> None:
                """Process job in background thread."""
                transcription_svc = TranscriptionService()
                diarization_svc = diarization_service  # Reuse from outer scope
                process_job(job_id_to_process, transcription_svc, diarization_svc)

            # Start processing in background thread
            worker_thread = threading.Thread(target=process_job_async, args=(job_id,), daemon=True)
            worker_thread.start()

            logger.info("WORKFLOW_WORKER_STARTED_FALLBACK", job_id=job_id, backend="threading")

        # Log audit trail
        try:
            audit_service.log_action(
                action="workflow_consult_started",
                user_id="system",
                resource=f"session:{x_session_id}",
                result="success",
                details={
                    "job_id": job_id,
                    "filename": audio.filename or "",
                    "workflow": "aurity_consult",
                    "audio_size": audio_size,
                },
            )
        except Exception as audit_error:
            logger.warning("AUDIT_LOG_FAILED", error=str(audit_error), job_id=job_id)

        logger.info(
            "WORKFLOW_CONSULT_STARTED",
            job_id=job_id,
            session_id=x_session_id,
        )

        return ConsultStartResponse(
            job_id=job_id,
            session_id=x_session_id,
            status="pending",
            message="Consultation workflow started. Use job_id to check progress.",
        )

    except ValueError as e:
        logger.warning(
            "WORKFLOW_CONSULT_VALIDATION_FAILED",
            session_id=x_session_id,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "WORKFLOW_CONSULT_FAILED",
            session_id=x_session_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start consultation workflow",
        )


@router.get(
    "/consult/{job_id}", response_model=ConsultStatusResponse, status_code=status.HTTP_200_OK
)
async def get_consult_status(job_id: str, retry_soap: bool = False) -> Any:
    """
    Get status of consultation workflow.

    **Orchestration Flow:**
    1. Get diarization job status (internal service)
    2. If completed, check if SOAP note exists
    3. Return unified status with all stages

    **Args:**
    - job_id: Job identifier from start_consult_workflow

    **Returns:**
    - Unified status of all workflow stages
    - SOAP note if workflow completed

    **Errors:**
    - 404: Job not found
    - 500: Status check failed
    """
    try:
        # Get services
        diarization_service = get_container().get_diarization_service()

        # Get diarization job
        job = diarization_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        # Build stages status based on job status
        stages = {
            "upload": "completed",
            "transcribe": "pending",  # Not implemented yet
            "diarize": "pending",  # Not implemented yet
            "soap": "pending",  # Not implemented yet
        }

        # Map job status to stages
        if job.status == "completed":
            stages["transcribe"] = "completed"
            stages["diarize"] = "completed"
            stages["soap"] = "completed"  # SOAP now available for completed jobs
        elif job.status == "processing":
            stages["transcribe"] = "processing"
            stages["diarize"] = "pending"
        elif job.status == "failed":
            stages["transcribe"] = "failed"

        soap_note = None
        result_data = None

        # Get result_data if job completed
        if job.status == "completed" and job.result_data:
            result_data = job.result_data

            # Check if SOAP note already exists in result_data
            soap_note_data = result_data.get("soap_note")
            soap_status = result_data.get("soap_status")

            # If retry_soap requested and status is failed, clear the failure to allow retry
            if retry_soap and soap_status == "failed":
                logger.info("SOAP_RETRY_REQUESTED", job_id=job_id)
                from backend.services.diarization.jobs import update_job

                result_data["soap_status"] = None
                result_data.pop("soap_error", None)  # Clear error message too
                update_job(job_id, result_data=result_data)
                soap_status = None

            if soap_note_data:
                soap_note = soap_note_data
                stages["soap"] = "completed"
            elif soap_status == "processing":
                stages["soap"] = "processing"
            elif soap_status == "failed":
                stages["soap"] = "failed"
            else:
                # Trigger background SOAP generation (non-blocking)
                stages["soap"] = "pending"

                # Start background worker if not already started
                if not soap_status:
                    from concurrent.futures import ThreadPoolExecutor
                    from concurrent.futures import TimeoutError as FuturesTimeoutError

                    from backend.services.diarization.jobs import update_job

                    def generate_soap_async(
                        job_id_to_process: str, result_data_to_process: dict
                    ) -> None:
                        """Generate SOAP in background thread with timeout protection."""
                        # Acquire semaphore to ensure only 1 SOAP generation at a time
                        acquired = _soap_worker_semaphore.acquire(blocking=False)
                        if not acquired:
                            logger.warning(
                                "WORKFLOW_SOAP_WORKER_BUSY",
                                job_id=job_id_to_process,
                                message="Another SOAP generation in progress, will retry on next poll",
                            )
                            return  # Exit without processing - client will retry on next GET

                        try:
                            # Mark as processing
                            updated_result = result_data_to_process.copy()
                            updated_result["soap_status"] = "processing"
                            update_job(job_id_to_process, result_data=updated_result)

                            def _generate_soap_with_timeout():
                                """Inner function to run Ollama with timeout."""
                                from backend.services.soap_generation.completeness import (
                                    CompletenessCalculator,
                                )
                                from backend.services.soap_generation.ollama_client import (
                                    OllamaClient,
                                )
                                from backend.services.soap_generation.soap_builder import (
                                    SOAPBuilder,
                                )

                                # Extract improved text from diarization segments
                                transcription_text = ""
                                if result_data_to_process.get("diarization", {}).get("segments"):
                                    segments = result_data_to_process["diarization"]["segments"]
                                    transcription_text = " ".join(
                                        seg.get("improved_text") or seg.get("text", "")
                                        for seg in segments
                                    )

                                if not transcription_text:
                                    transcription_text = result_data_to_process.get(
                                        "transcription", {}
                                    ).get("text", "")

                                if not transcription_text:
                                    raise ValueError("No transcription text available")

                                # Extract SOAP via Ollama (using qwen2.5 model) with timeout
                                ollama_client = OllamaClient(model="qwen2.5:7b-instruct-q4_0")
                                soap_data = ollama_client.extract_soap(transcription_text)

                                # Build SOAP models
                                subjetivo, objetivo, analisis, plan = SOAPBuilder.build(
                                    job_id_to_process, soap_data
                                )
                                completeness = CompletenessCalculator.calculate(
                                    subjetivo, objetivo, analisis, plan
                                )
                                soap_obj = SOAPBuilder.build_note(
                                    job_id_to_process,
                                    subjetivo,
                                    objetivo,
                                    analisis,
                                    plan,
                                    completeness,
                                )

                                return soap_obj

                            # Execute with 60s timeout to prevent system lockup
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(_generate_soap_with_timeout)
                                try:
                                    soap_obj = future.result(timeout=60.0)  # 60 second timeout

                                    # Store SOAP note in result_data (use mode='json' to serialize datetime)
                                    updated_result["soap_note"] = soap_obj.model_dump(mode="json")
                                    updated_result["soap_status"] = "completed"
                                    update_job(job_id_to_process, result_data=updated_result)

                                    logger.info(
                                        "WORKFLOW_SOAP_GENERATED_ASYNC",
                                        job_id=job_id_to_process,
                                        completeness=soap_obj.completeness,
                                    )
                                except FuturesTimeoutError:
                                    logger.error(
                                        "WORKFLOW_SOAP_TIMEOUT",
                                        job_id=job_id_to_process,
                                        timeout_sec=60,
                                    )
                                    updated_result["soap_status"] = "failed"
                                    updated_result[
                                        "soap_error"
                                    ] = "SOAP generation timeout (60s) - Ollama may be overloaded"
                                    update_job(job_id_to_process, result_data=updated_result)
                                except ValueError as ve:
                                    updated_result["soap_status"] = "failed"
                                    updated_result["soap_error"] = str(ve)
                                    update_job(job_id_to_process, result_data=updated_result)

                        except Exception as soap_error:
                            logger.error(
                                "WORKFLOW_SOAP_GENERATION_ASYNC_FAILED",
                                job_id=job_id_to_process,
                                error=str(soap_error),
                            )
                            updated_result = result_data_to_process.copy()
                            updated_result["soap_status"] = "failed"
                            updated_result["soap_error"] = str(soap_error)
                            update_job(job_id_to_process, result_data=updated_result)
                        finally:
                            # Always release semaphore
                            _soap_worker_semaphore.release()
                            logger.info("WORKFLOW_SOAP_WORKER_RELEASED", job_id=job_id_to_process)

                    # Start background thread
                    worker_thread = threading.Thread(
                        target=generate_soap_async, args=(job_id, result_data), daemon=True
                    )
                    worker_thread.start()
                    logger.info("WORKFLOW_SOAP_WORKER_STARTED", job_id=job_id)

        return ConsultStatusResponse(
            job_id=job_id,
            session_id=job.session_id,
            status=job.status,
            progress_pct=job.progress_percent or 0,
            stages=stages,
            soap_note=soap_note,
            result_data=result_data,
            error=job.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("WORKFLOW_STATUS_FAILED", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow status",
        )


@router.get("/consult", status_code=status.HTTP_200_OK)
async def list_consult_jobs(status_filter: Optional[str] = None) -> Any:
    """
    List all consultation workflow jobs.

    **Args:**
    - status_filter: Optional filter by status (completed, in_progress, pending, failed)

    **Returns:**
    - List of jobs with basic info (job_id, session_id, status, created_at)
    """
    try:
        # Get all jobs
        from backend.services.diarization.jobs import list_jobs

        all_jobs = list_jobs()

        # Filter by status if provided
        if status_filter:
            all_jobs = [job for job in all_jobs if job.status == status_filter]

        # Sort by created_at descending (most recent first)
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)

        # Return simplified job list with result_data for SOAP status
        return [
            {
                "job_id": job.job_id,
                "session_id": job.session_id,
                "status": job.status,
                "progress_pct": job.progress_percent or 0,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "audio_file_size": job.audio_file_size,
                "result_data": job.result_data,  # Include for SOAP status badges
            }
            for job in all_jobs
        ]

    except Exception as e:
        logger.error("LIST_JOBS_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )


@router.post(
    "/consult/stream", response_model=StreamChunkResponse, status_code=status.HTTP_202_ACCEPTED
)
async def process_audio_chunk(
    session_id: str = Form(...),
    chunk_number: int = Form(...),
    audio: UploadFile = File(...),
    mime: str = Form(""),
    timestamp_start: Optional[float] = Form(None),
    timestamp_end: Optional[float] = Form(None),
) -> StreamChunkResponse:
    """
    Process individual audio chunk (AUR-PROMPT-4.2 - PURE ORCHESTRATOR).

    **Architecture: PUBLIC layer (CRITICAL)**
    - PURE orchestrator: NO Services, ONLY calls INTERNAL endpoints
    - Returns job_id for async processing (202 Accepted)
    - Frontend polls /internal/transcribe/jobs/{job_id} for result

    **Workflow:**
    1. Validate session_id
    2. POST audio to /internal/transcribe/chunks (INTERNAL layer)
    3. Return job_id + queued status (no blocking)

    **Args:**
    - session_id: Session identifier (UUID4 format)
    - chunk_number: Sequential chunk number (0, 1, 2, ...)
    - audio: Audio segment (RecordRTC chunks with headers)
    - mime: MIME type from blob.type (e.g., "audio/webm")
    - timestamp_start: Start time in seconds (optional)
    - timestamp_end: End time in seconds (optional)

    **Returns:**
    - 202 Accepted with job_id
    - Frontend should poll GET /internal/transcribe/jobs/{job_id}

    **Errors:**
    - 400: Invalid session_id
    - 500: Failed to dispatch job

    **AUR-PROMPT-4.2 Compliance:**
    - ✅ PUBLIC layer: Pure orchestrator
    - ✅ Calls INTERNAL /internal/transcribe/chunks
    - ✅ Returns job_id (non-blocking)
    - ✅ Worker handles: WAV conversion + transcription + HDF5 append
    """
    try:
        # Validate session ID
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required field: session_id",
            )

        logger.info(
            "PUBLIC_CHUNK_RECEIVED",
            session_id=session_id,
            chunk_number=chunk_number,
            mime=mime,
        )

        # Call INTERNAL endpoint (pure orchestration)
        import httpx

        # Read audio content
        audio_content = await audio.read()

        # POST to INTERNAL /internal/transcribe/chunks
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:7001/internal/transcribe/chunks",
                files={
                    "audio": (f"chunk_{chunk_number}.webm", audio_content, mime or "audio/webm")
                },
                headers={
                    "X-Session-ID": session_id,
                    "X-Chunk-Number": str(chunk_number),
                },
                timeout=30.0,
            )

            if response.status_code != 202:
                logger.error(
                    "PUBLIC_INTERNAL_CALL_FAILED",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    status=response.status_code,
                    error=response.text,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal endpoint failed: {response.text}",
                )

            job_data = response.json()

        logger.info(
            "PUBLIC_JOB_CREATED",
            session_id=session_id,
            chunk_number=chunk_number,
            job_id=job_data.get("job_id"),
        )

        # Return job_id (non-blocking)
        return StreamChunkResponse(
            chunk_id=job_data.get("job_id", ""),
            session_id=session_id,
            chunk_number=chunk_number,
            transcription=None,  # Not available yet (async)
            speaker=None,
            timestamp_start=timestamp_start or 0.0,
            timestamp_end=timestamp_end or 0.0,
            status="queued",  # Job queued, not completed
            queued=True,
            job_id=job_data.get("job_id"),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "PUBLIC_VALIDATION_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "PUBLIC_ORCHESTRATION_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transcription job: {e!s}",
        )
