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

from typing import Any, Optional

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])


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
            stages["soap"] = "pending"  # TODO: Check SOAP service
        elif job.status == "processing":
            stages["transcribe"] = "processing"
            stages["diarize"] = "pending"
        elif job.status == "failed":
            stages["transcribe"] = "failed"

        soap_note = None
        # TODO: Get SOAP note from result_data if available

        return ConsultStatusResponse(
            job_id=job_id,
            session_id=job.session_id,
            status=job.status,
            progress_pct=job.progress_percent or 0,
            stages=stages,
            soap_note=soap_note,
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
