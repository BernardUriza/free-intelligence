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

import threading
from typing import Any, Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])

# Global semaphore to limit concurrent SOAP generation (max 1 at a time)
_soap_worker_semaphore = threading.Semaphore(1)


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
    result_data: Optional[dict] = Field(None, description="Full result data (transcription + diarization)")
    error: Optional[str] = Field(None, description="Error message if failed")


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

        # Orchestration Step 3: Trigger background processing
        # For MVP: Process synchronously in current request
        # TODO: For production: Use background queue (Celery/RQ/AWS SQS)
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

        logger.info("WORKFLOW_WORKER_STARTED", job_id=job_id)

        # Log audit trail (temporarily disabled due to HDF5 dtype issues)
        # TODO: Fix AuditService to handle string types in HDF5
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
async def get_consult_status(job_id: str) -> Any:
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
                    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

                    from backend.services.diarization.jobs import update_job

                    def generate_soap_async(job_id_to_process: str, result_data_to_process: dict) -> None:
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
                                from backend.services.soap_generation.ollama_client import OllamaClient
                                from backend.services.soap_generation.soap_builder import SOAPBuilder
                                from backend.services.soap_generation.completeness import CompletenessCalculator

                                # Extract improved text from diarization segments
                                transcription_text = ""
                                if result_data_to_process.get("diarization", {}).get("segments"):
                                    segments = result_data_to_process["diarization"]["segments"]
                                    transcription_text = " ".join(
                                        seg.get("improved_text") or seg.get("text", "")
                                        for seg in segments
                                    )

                                if not transcription_text:
                                    transcription_text = result_data_to_process.get("transcription", {}).get("text", "")

                                if not transcription_text:
                                    raise ValueError("No transcription text available")

                                # Extract SOAP via Ollama (using qwen2.5 model) with timeout
                                ollama_client = OllamaClient(model="qwen2.5:7b-instruct-q4_0")
                                soap_data = ollama_client.extract_soap(transcription_text)

                                # Build SOAP models
                                subjetivo, objetivo, analisis, plan = SOAPBuilder.build(job_id_to_process, soap_data)
                                completeness = CompletenessCalculator.calculate(subjetivo, objetivo, analisis, plan)
                                soap_obj = SOAPBuilder.build_note(job_id_to_process, subjetivo, objetivo, analisis, plan, completeness)

                                return soap_obj

                            # Execute with 60s timeout to prevent system lockup
                            with ThreadPoolExecutor(max_workers=1) as executor:
                                future = executor.submit(_generate_soap_with_timeout)
                                try:
                                    soap_obj = future.result(timeout=60.0)  # 60 second timeout

                                    # Store SOAP note in result_data (use mode='json' to serialize datetime)
                                    updated_result["soap_note"] = soap_obj.model_dump(mode='json')
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
                                    updated_result["soap_error"] = "SOAP generation timeout (60s) - Ollama may be overloaded"
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
                        target=generate_soap_async,
                        args=(job_id, result_data),
                        daemon=True
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
        # Get services
        diarization_service = get_container().get_diarization_service()

        # Get all jobs
        from backend.services.diarization.jobs import list_jobs

        all_jobs = list_jobs()

        # Filter by status if provided
        if status_filter:
            all_jobs = [job for job in all_jobs if job.status == status_filter]

        # Sort by created_at descending (most recent first)
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)

        # Return simplified job list
        return [
            {
                "job_id": job.job_id,
                "session_id": job.session_id,
                "status": job.status,
                "progress_pct": job.progress_percent or 0,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "audio_file_size": job.audio_file_size,
            }
            for job in all_jobs
        ]

    except Exception as e:
        logger.error("LIST_JOBS_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )
