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

File: backend/api/workflows.py
Created: 2025-11-08
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

        # Orchestration Step 1: Start diarization job
        # (Diarization service handles: file upload + transcription + speaker sep)
        job_result = diarization_service.start_job(
            session_id=x_session_id,
            audio_content=audio_content,
            filename=audio.filename or "audio",
            language="es",  # TODO: Auto-detect or from request
        )

        # Log audit trail
        audit_service.log_action(
            action="workflow_consult_started",
            user_id="system",
            resource=f"session:{x_session_id}",
            result="success",
            details={
                "job_id": job_result["job_id"],
                "filename": audio.filename,
                "workflow": "aurity_consult",
            },
        )

        logger.info(
            "WORKFLOW_CONSULT_STARTED",
            job_id=job_result["job_id"],
            session_id=x_session_id,
        )

        return ConsultStartResponse(
            job_id=job_result["job_id"],
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
        soap_service = get_container().get_soap_service()

        # Get diarization job status
        job_status = diarization_service.get_job_status(job_id)

        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        # Build stages status
        stages = {
            "upload": "completed",
            "transcribe": "completed" if job_status["status"] == "completed" else "in_progress",
            "diarize": "completed" if job_status["status"] == "completed" else "in_progress",
            "soap": "pending",
        }

        soap_note = None

        # If diarization completed, check SOAP
        if job_status["status"] == "completed":
            try:
                soap_result = soap_service.get_soap_for_job(job_id)
                if soap_result:
                    stages["soap"] = "completed"
                    soap_note = soap_result
            except Exception:
                # SOAP not generated yet or failed
                stages["soap"] = "pending"

        return ConsultStatusResponse(
            job_id=job_id,
            session_id=job_status["session_id"],
            status=job_status["status"],
            progress_pct=job_status.get("progress_pct", 0),
            stages=stages,
            soap_note=soap_note,
            error=job_status.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("WORKFLOW_STATUS_FAILED", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get workflow status",
        )
