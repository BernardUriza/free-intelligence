"""Timeline Verify API module.

Provides FastAPI router for hash verification functionality.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from .handlers import verify_hash
from .models import VerifyHashDetail, VerifyHashRequest, VerifyHashResponse

__all__ = [
    "router",
    "VerifyHashRequest",
    "VerifyHashResponse",
    "VerifyHashDetail",
]

# Create router for timeline verify endpoints
router = APIRouter()

# Mount endpoint handlers
router.post(
    "/verify-hash",
    response_model=VerifyHashResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify session/event hashes (batch)",
    description="Verifies SHA256 hashes for one or multiple sessions/events. Includes audit logging.",
)(verify_hash)
