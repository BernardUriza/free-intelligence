"""Triage API Router.

Triage intake flow

File: backend/api/triage/router.py
Created: 2025-11-08
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, constr, field_validator

from backend.container import get_container
from backend.logger import get_logger

from datetime import datetime
from typing import Any, Dict, Literal, Optional, Union

logger = get_logger(__name__)

router = APIRouter()

# ============================================================================
# MODELS
# ============================================================================


class IntakePayload(BaseModel):
    """Triage intake payload from frontend"""

    reason: constr(min_length=3)  # type: ignore
    symptoms: Union[str, list[str]] = []
    audioTranscription: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @field_validator("audioTranscription")
    @classmethod
    def validate_transcription_length(cls, v: Optional[str]) -> Optional[str]:
        """Limit audioTranscription to 32k chars"""
        if v and len(v) > 32_000:
            raise ValueError("audioTranscription exceeds 32k character limit")
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

    bufferId: str
    status: Literal["received"]
    receivedAt: datetime
    manifestUrl: str


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/intake", response_model=IntakeAck, status_code=status.HTTP_200_OK)
async def triage_intake(payload: IntakePayload, request: Request) -> IntakeAck:
    """
    Receive triage intake and store atomically in buffer directory.

    **Clean Code Architecture:**
    - TriageService handles buffer creation and storage
    - Uses DI container for dependency injection
    - AuditService logs all triage intakes

    Args:
        payload: Triage intake data
        request: FastAPI request object (for client IP)

    Returns:
        IntakeAck with bufferId and manifest URL

    Raises:
        HTTPException 500: Storage errors
    """
    try:
        # Get services from DI container
        triage_service = get_container().get_triage_service()
        audit_service = get_container().get_audit_service()

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
        received_at = datetime.fromisoformat(result["received_at"].replace("Z", "+00:00"))
        return IntakeAck(
            bufferId=result["buffer_id"],
            status="received",
            receivedAt=received_at,
            manifestUrl=result["manifest_url"],
        )

    except OSError as e:
        logger.warning(f"TRIAGE_INTAKE_STORAGE_FAILED: {e!s}")
        raise HTTPException(status_code=500, detail=f"Failed to store triage intake: {e!s}") from e
    except Exception as e:
        logger.error(f"TRIAGE_INTAKE_FAILED: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to process triage intake") from e


@router.get("/manifest/{buffer_id}")
async def get_manifest(buffer_id: str) -> dict[str, Any]:
    """
    Retrieve manifest for a triage buffer.

    **Clean Code Architecture:**
    - TriageService handles manifest retrieval
    - Uses DI container for dependency injection
    - AuditService logs all manifest retrievals

    Args:
        buffer_id: Buffer identifier

    Returns:
        Manifest JSON

    Raises:
        HTTPException 404: Buffer not found
    """
    try:
        # Get services from DI container
        triage_service = get_container().get_triage_service()
        audit_service = get_container().get_audit_service()

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
