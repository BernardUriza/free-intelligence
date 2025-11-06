"""Endpoint handlers for export API.

Implements the FastAPI endpoint functions for export operations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from fastapi.responses import FileResponse

from backend.container import get_container

from .config import EXPORT_DIR, logger
from .models import (
    ExportRequest,
    ExportResponse,
    VerifyRequest,
    VerifyResponse,
    VerifyResult,
)
from .utils import (
    build_artifacts_from_result,
    generate_manifest_url,
    log_export_created,
    log_export_retrieved,
    log_export_verified,
)


async def create_export(request: ExportRequest) -> ExportResponse:
    """Create export bundle for session.

    **Clean Code Architecture:**
    - ExportService handles export creation with manifest generation
    - Uses DI container for dependency injection
    - AuditService logs all export creations

    Args:
        request: Export request with session ID, formats, and inclusions

    Returns:
        Export response with artifacts and manifest URL

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
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
                    "session_id": request.session_id,
                    "format": fmt,
                    "include": request.include.model_dump(),
                    "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
                },
                indent=2,
            )

        # Delegate to service for export creation
        result = export_service.create_export(
            session_id=request.session_id,
            content_dict=content_dict,
            formats=request.formats,
        )

        # Build artifacts with download URLs
        artifacts = build_artifacts_from_result(result["export_id"], result["artifacts"])
        manifest_url = generate_manifest_url(result["export_id"])

        # Log audit trail
        audit_service.log_action(
            action="export_created",
            user_id="system",
            resource=f"export:{result['export_id']}",
            result="success",
            details={"session_id": request.session_id, "formats": request.formats},
        )

        log_export_created(result["export_id"], request.session_id, request.formats)

        return ExportResponse(
            export_id=result["export_id"],
            status="ready",
            artifacts=artifacts,
            manifest_url=manifest_url,
        )

    except ValueError as e:
        logger.warning("EXPORT_CREATION_VALIDATION_FAILED: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("EXPORT_CREATION_FAILED: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create export: {e!s}") from e


async def get_export(export_id: str) -> ExportResponse:
    """Get export status and metadata.

    **Clean Code Architecture:**
    - ExportService handles metadata retrieval
    - Uses DI container for dependency injection

    Args:
        export_id: Export identifier

    Returns:
        Export metadata (same as POST response)

    Raises:
        HTTPException: 404 if export not found, 500 for server errors
    """
    try:
        # Get services from DI container
        export_service = get_container().get_export_service()
        audit_service = get_container().get_audit_service()

        # Delegate to service for metadata retrieval
        metadata = export_service.get_export_metadata(export_id)

        if not metadata:
            logger.warning("EXPORT_NOT_FOUND: export_id=%s", export_id)
            raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

        # Build artifacts with download URLs
        artifacts = build_artifacts_from_result(export_id, metadata["artifacts"])
        manifest_url = generate_manifest_url(export_id)

        # Log audit trail
        audit_service.log_action(
            action="export_retrieved",
            user_id="system",
            resource=f"export:{export_id}",
            result="success",
        )

        log_export_retrieved(export_id)

        return ExportResponse(
            export_id=export_id,
            status="ready",
            artifacts=artifacts,
            manifest_url=manifest_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "EXPORT_RETRIEVAL_FAILED: export_id=%s, error=%s",
            export_id,
            str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve export: {e!s}") from e


async def verify_export(export_id: str, request: VerifyRequest) -> VerifyResponse:
    """Verify export file integrity.

    **Clean Code Architecture:**
    - ExportService handles verification with hash validation
    - Uses DI container for dependency injection

    Args:
        export_id: Export identifier
        request: Verify request with target files

    Returns:
        Verification results with per-target status

    Raises:
        HTTPException: 404 if export not found, 500 for server errors

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
        results = [
            VerifyResult(
                target=result["target"],
                ok=result["ok"],
                message=result.get("message"),
            )
            for result in verify_result["results"]
        ]

        # Log audit trail
        audit_service.log_action(
            action="export_verified",
            user_id="system",
            resource=f"export:{export_id}",
            result="success" if verify_result["ok"] else "failure",
            details={"targets": request.targets, "all_ok": verify_result["ok"]},
        )

        log_export_verified(export_id, verify_result["ok"])

        return VerifyResponse(ok=verify_result["ok"], results=results)

    except HTTPException:
        raise
    except OSError as e:
        logger.warning("EXPORT_VERIFICATION_FAILED: export_id=%s, error=%s", export_id, str(e))
        raise HTTPException(status_code=404, detail=f"Export not found: {e!s}") from e
    except Exception as e:
        logger.error("EXPORT_VERIFICATION_FAILED: export_id=%s, error=%s", export_id, str(e))
        raise HTTPException(status_code=500, detail=f"Failed to verify export: {e!s}") from e


async def download_file(export_id: str, filename: str) -> FileResponse:
    """Download export file (alternative to static serving).

    Args:
        export_id: Export identifier
        filename: File to download (session.md, session.json, manifest.json)

    Returns:
        File content as attachment

    Raises:
        HTTPException: 404 if file not found
    """
    export_path = EXPORT_DIR / export_id
    filepath = export_path / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    return FileResponse(filepath, media_type="application/octet-stream", filename=filename)
