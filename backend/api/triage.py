from __future__ import annotations

"""
Triage API - Intake endpoint for conversation capture
Card: FI-API-FEAT-014

Endpoints:
  POST /api/triage/intake - Receive triage intake with optional audio transcription
"""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Optional, Union
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, constr, field_validator

# Import audit logger
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/triage", tags=["triage"])

# Data directory for triage buffers
DATA_DIR = Path(os.getenv("TRIAGE_DATA_DIR", "./data/triage_buffers"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# MODELS
# ============================================================================


class IntakePayload(BaseModel):
    """Triage intake payload from frontend"""

    reason: constr(min_length=3)  # type: ignore
    symptoms: Union[str, list[str]] = []
    audioTranscription: Optional[str] = None
    metadata: dict[str, Any] = {}

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

    Steps:
    1. Generate unique bufferId
    2. Create buffer directory
    3. Write intake.json atomically with fsync
    4. Generate manifest with SHA256 hash
    5. Log audit event
    6. Return acknowledgment

    Args:
        payload: Triage intake data
        request: FastAPI request object (for client IP)

    Returns:
        IntakeAck with bufferId and manifest URL

    Raises:
        HTTPException 422: Validation errors
        HTTPException 500: Storage errors
    """
    # Generate unique buffer ID
    buffer_id = f"tri_{uuid4().hex}"
    buffer_dir = DATA_DIR / buffer_id

    try:
        # Create buffer directory
        buffer_dir.mkdir(parents=True, exist_ok=True)

        # Prepare intake data
        intake_data = {
            "bufferId": buffer_id,
            "receivedAt": datetime.now(UTC).isoformat() + "Z",
            "payload": payload.model_dump(),
            "client": {
                "ip": request.client.host if request.client else "unknown",
                "userAgent": request.headers.get("user-agent", "unknown"),
            },
        }

        # Compute payload hash (SHA256)
        payload_json = json.dumps(payload.model_dump(), sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()

        # Create manifest
        manifest = {
            "version": "1.0.0",
            "bufferId": buffer_id,
            "receivedAt": intake_data["receivedAt"],
            "payloadHash": f"sha256:{payload_hash}",
            "payloadSubset": {
                "reason": payload.reason[:100],  # First 100 chars
                "symptomsCount": len(payload.symptoms),
                "hasTranscription": payload.audioTranscription is not None,
            },
            "metadata": payload.metadata,
        }

        # Write intake.json atomically
        intake_path = buffer_dir / "intake.json"
        intake_tmp = buffer_dir / "intake.json.tmp"

        with open(intake_tmp, "w") as f:
            json.dump(intake_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Atomic write guarantee

        # Atomic rename
        intake_tmp.rename(intake_path)

        # Write manifest.json
        manifest_path = buffer_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Log audit event
        logger.info(
            "TRIAGE_INTAKE_RECEIVED",
            bufferId=buffer_id,
            bytes=len(payload_json),
            ip=intake_data["client"]["ip"],
            symptomsCount=len(payload.symptoms),
            hasTranscription=payload.audioTranscription is not None,
            payloadHash=payload_hash,
        )

        # Return acknowledgment
        received_at = datetime.fromisoformat(intake_data["receivedAt"].replace("Z", "+00:00"))
        return IntakeAck(
            bufferId=buffer_id,
            status="received",
            receivedAt=received_at,
            manifestUrl=f"/api/triage/manifest/{buffer_id}",
        )

    except Exception as e:
        logger.error(
            "TRIAGE_INTAKE_FAILED",
            bufferId=buffer_id,
            error=str(e),
            errorType=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store triage intake: {str(e)}",
        ) from e


@router.get("/manifest/{buffer_id}")
async def get_manifest(buffer_id: str) -> dict[str, Any]:
    """
    Retrieve manifest for a triage buffer.

    Args:
        buffer_id: Buffer identifier

    Returns:
        Manifest JSON

    Raises:
        HTTPException 404: Buffer not found
    """
    manifest_path = DATA_DIR / buffer_id / "manifest.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Manifest not found for buffer {buffer_id}",
        )

    with open(manifest_path) as f:
        return json.load(f)
