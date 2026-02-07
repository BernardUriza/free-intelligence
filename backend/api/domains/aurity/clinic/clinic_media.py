"""Clinic Media Router - Stub Implementation.

⚠️ STUB: Returns 501 Not Implemented until full implementation ready.

This stub serves multiple purposes:
1. Documents the API shape for clinic media endpoints
2. Allows tests to run (not skip) with expected 501 responses
3. Provides clear error messages for frontend developers
4. Will be replaced with full implementation when storage layer ready

Endpoints (4 total):
- POST   /clinic-media/upload - Upload media (STUB)
- GET    /clinic-media/list - List media (STUB)
- PUT    /clinic-media/{id} - Update media (STUB)
- DELETE /clinic-media/{id} - Delete media (STUB)

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Migrated from: backend/api/routers/clinic/public/clinic_media_stub.py
Status: STUB (replace with full implementation when storage layer ready)
"""

from __future__ import annotations

from fastapi import APIRouter, Form, File, UploadFile, Depends, status
from fastapi.responses import JSONResponse

from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def upload_clinic_media_stub(
    media_type: str = Form(...),
    message_content: str | None = Form(None),
    clinic_id: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
):
    """Upload clinic media (STUB - not implemented yet).

    Once implemented, this endpoint will:
    - Accept file uploads (images, videos, PDFs)
    - Validate clinic_id matches current_user.clinic_id
    - Store media in clinic-specific storage (S3/Azure Blob)
    - Return media metadata

    Security:
    - Validates clinic_id to prevent cross-clinic uploads
    - SUPERADMIN can upload to any clinic

    Returns:
        501 Not Implemented with clear message
    """
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": "Not implemented yet",
            "message": "Clinic media upload functionality is under development",
            "endpoint": "/api/clinic-media/upload",
            "expected_implementation": "Phase 3 - Storage Layer",
            "provided_params": {
                "media_type": media_type,
                "clinic_id": clinic_id or current_user.clinic_id,
                "has_file": file is not None,
            }
        }
    )


@router.get("/list", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_clinic_media_stub(
    current_user: User = Depends(get_current_user),
):
    """List clinic media (STUB - not implemented yet).

    Once implemented, this endpoint will:
    - List all media for user's clinic
    - Filter by media_type (image, video, document)
    - Paginate results
    - Return metadata (filename, upload_date, size)

    Security:
    - Filters by current_user.clinic_id
    - SUPERADMIN can list media from any clinic

    Returns:
        501 Not Implemented with clear message
    """
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": "Not implemented yet",
            "message": "Clinic media listing functionality is under development",
            "endpoint": "/api/clinic-media/list",
            "expected_implementation": "Phase 3 - Storage Layer",
            "user_clinic": current_user.clinic_id,
        }
    )


@router.put("/{media_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_clinic_media_stub(
    media_id: str,
    current_user: User = Depends(get_current_user),
):
    """Update clinic media metadata (STUB - not implemented yet)."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": "Not implemented yet",
            "message": "Clinic media update functionality is under development",
            "endpoint": f"/api/clinic-media/{media_id}",
        }
    )


@router.delete("/{media_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_clinic_media_stub(
    media_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete clinic media (STUB - not implemented yet)."""
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": "Not implemented yet",
            "message": "Clinic media deletion functionality is under development",
            "endpoint": f"/api/clinic-media/{media_id}",
        }
    )


__all__ = ["router"]
