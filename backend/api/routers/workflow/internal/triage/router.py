"""Triage API Router (REFACTORED with DI).

REFACTORED: Uses FastAPI Depends() instead of inline get_container().

Triage intake flow

File: backend/api/triage/router.py
Created: 2025-11-08
Refactored: 2026-01-28 (Phase 2.3 - DI pattern)
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Union

from backend.api.audit.services.audit_service import AuditService
from backend.services.workflow.dependencies import (
    get_audit_service_dep,
    get_triage_service_dep,
)
from backend.services.workflow.services.triage_service import TriageService
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, constr, field_validator

logger = get_logger(__name__)

router = APIRouter()

# ============================================================================
# MODELS
# ============================================================================


class IntakePayload(BaseModel):
    """Triage intake payload from frontend"""

    reason: constr(min_length=3)  # type: ignore
    symptoms: Union[str, list[str]] = []
    audio_transcription: str | None = None
    metadata: dict[str, Any] = {}

    @field_validator("audio_transcription")
    @classmethod
    def validate_transcription_length(cls, v: str | None) -> str | None:
        """Limit audio_transcription to 32k chars"""
        if v and len(v) > 32_000:
            raise ValueError("audio_transcription exceeds 32k character limit")
        return v

    @field_validator("symptoms")
    @classmethod
    def normalize_symptoms(cls, v: Union[str, list[str]]) -> list[str]:
        """Normalize symptoms to list"""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


class IntakeAck(BaseModel):
    """Acknowledgment response for intake"""

    buffer_id: str
    status: Literal["received"]
    received_at: datetime
    manifest_url: str


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/intake", response_model=IntakeAck, status_code=status.HTTP_200_OK)
async def triage_intake(
    payload: IntakePayload,
    request: Request,
    triage_service: TriageService = Depends(get_triage_service_dep),
    audit_service: AuditService = Depends(get_audit_service_dep),
) -> IntakeAck:
    """
    Receive triage intake and store atomically in buffer directory (REFACTORED with DI).

    **Clean Code Architecture:**
    - TriageService handles buffer creation and storage
    - Uses FastAPI Depends() for dependency injection
    - AuditService logs all triage intakes

    Args:
        payload: Triage intake data
        request: FastAPI request object (for client IP)
        triage_service: Triage service (injected by FastAPI)
        audit_service: Audit service (injected by FastAPI)

    Returns:
        IntakeAck with bufferId and manifest URL

    Raises:
        HTTPException 500: Storage errors
    """
    try:

        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Delegate to service
        result = triage_service.create_buffer(
            payload=payload.model_dump(),
            client_ip=client_ip,
            user_agent=user_agent,
        )

        # Log audit trail
        audit_service.log_action(
            action="triage_intake_received",
            user_id="system",
            resource=f"triage_buffer:{result['buffer_id']}",
            result="success",
            details={
                "payload_hash": result["payload_hash"],
                "client_ip": client_ip,
            },
        )

        logger.info(
            f"TRIAGE_INTAKE_RECEIVED: buffer_id={result['buffer_id']}, payload_hash={result['payload_hash']}, ip={client_ip}"
        )

        # Return acknowledgment
        received_at_dt = datetime.fromisoformat(result["received_at"].replace("Z", "+00:00"))
        return IntakeAck(
            buffer_id=result["buffer_id"],
            status="received",
            received_at=received_at_dt,
            manifest_url=result["manifest_url"],
        )

    except OSError as e:
        logger.warning(f"TRIAGE_INTAKE_STORAGE_FAILED: {e!s}")
        raise HTTPException(status_code=500, detail=f"Failed to store triage intake: {e!s}") from e
    except Exception as e:
        logger.error(f"TRIAGE_INTAKE_FAILED: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to process triage intake") from e


@router.get("/manifest/{buffer_id}")
async def get_manifest(
    buffer_id: str,
    triage_service: TriageService = Depends(get_triage_service_dep),
    audit_service: AuditService = Depends(get_audit_service_dep),
) -> dict[str, Any]:
    """
    Retrieve manifest for a triage buffer (REFACTORED with DI).

    **Clean Code Architecture:**
    - TriageService handles manifest retrieval
    - Uses FastAPI Depends() for dependency injection
    - AuditService logs all manifest retrievals

    Args:
        buffer_id: Buffer identifier
        triage_service: Triage service (injected by FastAPI)
        audit_service: Audit service (injected by FastAPI)

    Returns:
        Manifest JSON

    Raises:
        HTTPException 404: Buffer not found
    """
    try:

        # Delegate to service
        result = triage_service.get_manifest(buffer_id)

        if not result:
            logger.warning(f"TRIAGE_MANIFEST_NOT_FOUND: buffer_id={buffer_id}")
            raise HTTPException(
                status_code=404, detail=f"Manifest not found for buffer {buffer_id}"
            )

        # Log audit trail
        audit_service.log_action(
            action="triage_manifest_retrieved",
            user_id="system",
            resource=f"triage_buffer:{buffer_id}",
            result="success",
        )

        logger.info(f"TRIAGE_MANIFEST_RETRIEVED: buffer_id={buffer_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TRIAGE_MANIFEST_RETRIEVAL_FAILED: buffer_id={buffer_id}, error={e!s}")
        raise HTTPException(status_code=500, detail="Failed to retrieve manifest") from e
