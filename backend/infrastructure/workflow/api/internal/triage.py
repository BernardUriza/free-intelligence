"""Triage API Router (REFACTORED with DI).

Triage intake flow with buffer storage.

Python 2026 patterns:
- Annotated[T, Depends(...)] for cleaner DI
- `|` union syntax for type hints
- Literal types for constrained values
- field_validator with @classmethod for Pydantic v2

Endpoints:
- POST /intake - Receive triage intake and store atomically
- GET /manifest/{buffer_id} - Retrieve manifest for buffer

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/workflow/internal/triage/router.py
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, constr, field_validator

from backend.services.audit.services.audit_service import AuditService
from backend.services.audit.dependencies import get_audit_service_dep
from backend.services.workflow.dependencies import get_triage_service_dep
from backend.services.workflow.services.triage_service import TriageService
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class IntakePayload(BaseModel):
    """Triage intake payload from frontend."""

    reason: constr(min_length=3)  # type: ignore[valid-type]
    symptoms: str | list[str] = []
    audio_transcription: str | None = None
    metadata: dict[str, Any] = {}

    @field_validator("audio_transcription")
    @classmethod
    def validate_transcription_length(cls, v: str | None) -> str | None:
        """Limit audio_transcription to 32k chars."""
        if v and len(v) > 32_000:
            raise ValueError("audio_transcription exceeds 32k character limit")
        return v

    @field_validator("symptoms")
    @classmethod
    def normalize_symptoms(cls, v: str | list[str]) -> list[str]:
        """Normalize symptoms to list."""
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


class IntakeAck(BaseModel):
    """Acknowledgment response for intake."""

    buffer_id: str
    status: Literal["received"]
    received_at: datetime
    manifest_url: str


@router.post("/intake", response_model=IntakeAck, status_code=status.HTTP_200_OK)
async def triage_intake(
    payload: IntakePayload,
    request: Request,
    triage_service: Annotated[TriageService, Depends(get_triage_service_dep)],
    audit_service: Annotated[AuditService, Depends(get_audit_service_dep)],
) -> IntakeAck:
    """Receive triage intake and store atomically in buffer directory.

    Args:
        payload: Triage intake data
        request: FastAPI request object (for client IP)
        triage_service: Triage service (injected)
        audit_service: Audit service (injected)

    Returns:
        IntakeAck with bufferId and manifest URL

    Raises:
        HTTPException 500: Storage errors
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        result = triage_service.create_buffer(
            payload=payload.model_dump(),
            client_ip=client_ip,
            user_agent=user_agent,
        )

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
            "TRIAGE_INTAKE_RECEIVED",
            buffer_id=result["buffer_id"],
            payload_hash=result["payload_hash"],
            ip=client_ip,
        )

        received_at_dt = datetime.fromisoformat(result["received_at"].replace("Z", "+00:00"))
        return IntakeAck(
            buffer_id=result["buffer_id"],
            status="received",
            received_at=received_at_dt,
            manifest_url=result["manifest_url"],
        )

    except OSError as e:
        logger.warning("TRIAGE_INTAKE_STORAGE_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to store triage intake: {e!s}") from e
    except Exception as e:
        logger.error("TRIAGE_INTAKE_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process triage intake") from e


@router.get("/manifest/{buffer_id}")
async def get_manifest(
    buffer_id: str,
    triage_service: Annotated[TriageService, Depends(get_triage_service_dep)],
    audit_service: Annotated[AuditService, Depends(get_audit_service_dep)],
) -> dict[str, Any]:
    """Retrieve manifest for a triage buffer.

    Args:
        buffer_id: Buffer identifier
        triage_service: Triage service (injected)
        audit_service: Audit service (injected)

    Returns:
        Manifest JSON

    Raises:
        HTTPException 404: Buffer not found
    """
    try:
        result = triage_service.get_manifest(buffer_id)

        if not result:
            logger.warning("TRIAGE_MANIFEST_NOT_FOUND", buffer_id=buffer_id)
            raise HTTPException(
                status_code=404, detail=f"Manifest not found for buffer {buffer_id}"
            )

        audit_service.log_action(
            action="triage_manifest_retrieved",
            user_id="system",
            resource=f"triage_buffer:{buffer_id}",
            result="success",
        )

        logger.info("TRIAGE_MANIFEST_RETRIEVED", buffer_id=buffer_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TRIAGE_MANIFEST_RETRIEVAL_FAILED", buffer_id=buffer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve manifest") from e
