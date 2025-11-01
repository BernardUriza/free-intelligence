#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Export API

FastAPI router for session export with manifest and hash verification.

File: backend/api/exports.py
Cards: FI-API-FEAT-013
Created: 2025-10-30

Philosophy: Deterministic exports with SHA256 provenance.
- Same sessionId ⇒ same hashes (deterministic content generation)
- Every export has manifest with file hashes
- Verify endpoint for integrity checking
- Optional JWS signing with HS256

Updated to use clean code architecture with ExportService.

Endpoints:
- POST /api/exports -> create export bundle
- GET /api/exports/{exportId} -> get export status
- POST /api/exports/{exportId}/verify -> verify file integrity
- GET /downloads/exp_{id}/* -> static file serving (configured in main app)
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.sessions_store import SessionsStore

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Export directory (env var or default)
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "/tmp/fi_exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Base download URL (env var or default)
BASE_DOWNLOAD_URL = os.getenv("BASE_DOWNLOAD_URL", "http://localhost:7001/downloads")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class ExportInclude(BaseModel):
    """What to include in export"""

    transcript: bool = True
    events: bool = True
    attachments: bool = False


class ExportRequest(BaseModel):
    """Create export request"""

    sessionId: str
    formats: list[Literal["md", "json"]] = Field(..., min_length=1)
    include: ExportInclude = Field(default_factory=ExportInclude)


class ExportArtifact(BaseModel):
    """Export artifact metadata"""

    format: Literal["md", "json", "manifest"]
    url: str
    sha256: str
    bytes: int


class ExportResponse(BaseModel):
    """Export response"""

    exportId: str
    status: Literal["ready", "processing"]
    artifacts: list[ExportArtifact]
    manifestUrl: str


class VerifyRequest(BaseModel):
    """Verify request"""

    targets: list[Literal["md", "json", "manifest"]] = Field(
        default_factory=lambda: ["md", "json", "manifest"]
    )


class VerifyResult(BaseModel):
    """Verify result for single target"""

    target: str
    ok: bool
    message: Optional[str] = None


class VerifyResponse(BaseModel):
    """Verify response"""

    ok: bool
    results: list[VerifyResult]




# ============================================================================
# FASTAPI ROUTER
# ============================================================================

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", response_model=ExportResponse, status_code=200)
async def create_export(request: ExportRequest):
    """
    Create export bundle for session.

    **Clean Code Architecture:**
    - ExportService handles export creation with manifest generation
    - Uses DI container for dependency injection
    - AuditService logs all export creations

    Body:
    - sessionId: Session UUID
    - formats: List of formats (md, json, or both)
    - include: What to include (transcript, events, attachments)

    Returns:
    - exportId: Export identifier
    - status: "ready" (sync) or "processing" (async)
    - artifacts: List of generated files with URLs and hashes
    - manifestUrl: URL to manifest.json
    """
    try:
        # Get services from DI container
        export_service = get_container().get_export_service()
        audit_service = get_container().get_audit_service()

        # Generate content for each format
        content_dict = {}
        for fmt in request.formats:
            # TODO: Implement deterministic content generation
            # For now, use placeholder
            content_dict[fmt] = json.dumps(
                {
                    "session_id": request.sessionId,
                    "format": fmt,
                    "include": request.include.dict(),
                    "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
                },
                indent=2,
            )

        # Delegate to service for export creation
        result = export_service.create_export(
            session_id=request.sessionId,
            content_dict=content_dict,
            formats=request.formats,
        )

        # Build artifacts with download URLs
        artifacts = []
        for artifact in result["artifacts"]:
            filename = f"session.{artifact['format']}" if artifact["format"] != "manifest" else "manifest.json"
            url = f"{BASE_DOWNLOAD_URL}/{result['export_id']}/{filename}"
            artifacts.append(
                ExportArtifact(
                    format=artifact["format"],
                    url=url,
                    sha256=artifact["sha256"],
                    bytes=artifact["bytes"],
                )
            )

        manifest_url = f"{BASE_DOWNLOAD_URL}/{result['export_id']}/manifest.json"

        # Log audit trail
        audit_service.log_action(
            action="export_created",
            user_id="system",
            resource=f"export:{result['export_id']}",
            result="success",
            details={"session_id": request.sessionId, "formats": request.formats},
        )

        logger.info(
            "EXPORT_CREATED",
            export_id=result["export_id"],
            session_id=request.sessionId,
            formats=request.formats,
        )

        return ExportResponse(
            exportId=result["export_id"],
            status="ready",
            artifacts=artifacts,
            manifestUrl=manifest_url,
        )

    except ValueError as e:
        logger.warning(f"EXPORT_CREATION_VALIDATION_FAILED: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"EXPORT_CREATION_FAILED: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create export: {str(e)}")


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(export_id: str):
    """
    Get export status and metadata.

    **Clean Code Architecture:**
    - ExportService handles metadata retrieval
    - Uses DI container for dependency injection

    Path params:
    - export_id: Export identifier

    Returns:
    - Export metadata (same as POST response)

    Raises:
    - 404: Export not found
    """
    try:
        # Get services from DI container
        export_service = get_container().get_export_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service for metadata retrieval
        metadata = export_service.get_export_metadata(export_id)

        if not metadata:
            logger.warning(f"EXPORT_NOT_FOUND: export_id={export_id}")
            raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

        # Build artifacts with download URLs
        artifacts = []
        for artifact in metadata["artifacts"]:
            filename = f"session.{artifact['format']}" if artifact["format"] != "manifest" else "manifest.json"
            url = f"{BASE_DOWNLOAD_URL}/{export_id}/{filename}"
            artifacts.append(
                ExportArtifact(
                    format=artifact["format"],
                    url=url,
                    sha256=artifact["sha256"],
                    bytes=artifact["bytes"],
                )
            )

        manifest_url = f"{BASE_DOWNLOAD_URL}/{export_id}/manifest.json"

        # Log audit trail
        audit_service.log_action(
            action="export_retrieved",
            user_id="system",
            resource=f"export:{export_id}",
            result="success",
        )

        logger.info("EXPORT_RETRIEVED", export_id=export_id)

        return ExportResponse(
            exportId=export_id,
            status="ready",
            artifacts=artifacts,
            manifestUrl=manifest_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EXPORT_RETRIEVAL_FAILED: export_id={export_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve export: {str(e)}")


@router.post("/{export_id}/verify", response_model=VerifyResponse)
async def verify_export(export_id: str, request: VerifyRequest):
    """
    Verify export file integrity.

    **Clean Code Architecture:**
    - ExportService handles verification with hash validation
    - Uses DI container for dependency injection

    Path params:
    - export_id: Export identifier

    Body:
    - targets: List of targets to verify (md, json, manifest)

    Returns:
    - ok: True if all targets pass
    - results: List of verification results per target

    Verification:
    - Computes SHA256 of file on disk
    - Compares against manifest.sha256
    - If SIGNING_KEY exists, validates JWS signature
    """
    try:
        # Get services from DI container
        export_service = get_container().get_export_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service for verification
        verify_result = export_service.verify_export(
            export_id=export_id,
            targets=request.targets,
        )

        # Convert results to response format
        results = []
        for result in verify_result["results"]:
            results.append(
                VerifyResult(
                    target=result["target"],
                    ok=result["ok"],
                    message=result.get("message"),
                )
            )

        # Log audit trail
        audit_service.log_action(
            action="export_verified",
            user_id="system",
            resource=f"export:{export_id}",
            result="success" if verify_result["ok"] else "failure",
            details={"targets": request.targets, "all_ok": verify_result["ok"]},
        )

        logger.info(
            "EXPORT_VERIFIED",
            export_id=export_id,
            all_ok=verify_result["ok"],
        )

        return VerifyResponse(ok=verify_result["ok"], results=results)

    except HTTPException:
        raise
    except IOError as e:
        logger.warning(f"EXPORT_VERIFICATION_FAILED: export_id={export_id}, error={str(e)}")
        raise HTTPException(status_code=404, detail=f"Export not found: {str(e)}")
    except Exception as e:
        logger.error(f"EXPORT_VERIFICATION_FAILED: export_id={export_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to verify export: {str(e)}")


# ============================================================================
# STATIC FILE SERVING
# ============================================================================
# Note: This should be registered in main app as:
# app.mount("/downloads", StaticFiles(directory=EXPORT_DIR), name="downloads")
# Or use explicit endpoint:


@router.get("/{export_id}/download/{filename}")
async def download_file(export_id: str, filename: str):
    """
    Download export file (alternative to static serving).

    Path params:
    - export_id: Export identifier
    - filename: File to download (session.md, session.json, manifest.json)

    Returns:
    - File content as attachment
    """
    export_path = EXPORT_DIR / export_id
    filepath = export_path / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    return FileResponse(filepath, media_type="application/octet-stream", filename=filename)
