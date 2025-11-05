"""Export API module.

Provides FastAPI router for session export functionality.
"""

from __future__ import annotations

from fastapi import APIRouter

from .handlers import create_export, download_file, get_export, verify_export
from .models import ExportRequest, ExportResponse, VerifyRequest, VerifyResponse

__all__ = [
    "router",
    "ExportRequest",
    "ExportResponse",
    "VerifyRequest",
    "VerifyResponse",
]

# Create router for export endpoints
router = APIRouter()

# Mount endpoint handlers
router.post("", response_model=ExportResponse, status_code=200)(create_export)
router.get("/{export_id}", response_model=ExportResponse)(get_export)
router.post("/{export_id}/verify", response_model=VerifyResponse)(verify_export)
router.get("/{export_id}/download/{filename}")(download_file)
