"""Utility functions for export API.

Provides helper functions for artifact building, URL generation, and logging.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .config import BASE_DOWNLOAD_URL, logger
from .models import ExportArtifact


def build_artifact_filename(fmt: str) -> str:
    """Generate filename for export artifact.

    Args:
        fmt: Export format (md, json, manifest)

    Returns:
        Filename with appropriate extension
    """
    if fmt == "manifest":
        return "manifest.json"
    return f"session.{fmt}"


def build_artifact_url(export_id: str, filename: str) -> str:
    """Generate download URL for artifact.

    Args:
        export_id: Export identifier
        filename: Artifact filename

    Returns:
        Full download URL
    """
    return f"{BASE_DOWNLOAD_URL}/{export_id}/{filename}"


def build_artifacts_from_result(
    export_id: str,
    artifacts: list[Mapping[str, Any]],
) -> list[ExportArtifact]:
    """Convert artifact metadata to ExportArtifact models.

    Args:
        export_id: Export identifier
        artifacts: List of artifact metadata dicts from ExportService

    Returns:
        List of ExportArtifact Pydantic models with URLs
    """
    result = []
    for artifact in artifacts:
        filename = build_artifact_filename(artifact["format"])
        url = build_artifact_url(export_id, filename)
        result.append(
            ExportArtifact(
                format=artifact["format"],
                url=url,
                sha256=artifact["sha256"],
                bytes=artifact["bytes"],
            )
        )
    return result


def generate_manifest_url(export_id: str) -> str:
    """Generate URL for manifest.json.

    Args:
        export_id: Export identifier

    Returns:
        Manifest download URL
    """
    return build_artifact_url(export_id, "manifest.json")


def log_export_created(
    export_id: str,
    session_id: str,
    formats: Sequence[str],
) -> None:
    """Log export creation action.

    Args:
        export_id: Export identifier
        session_id: Session identifier
        formats: List of export formats
    """
    logger.info(
        "EXPORT_CREATED: export_id=%s, session_id=%s, formats=%s",
        export_id,
        session_id,
        formats,
    )


def log_export_retrieved(export_id: str) -> None:
    """Log export retrieval action.

    Args:
        export_id: Export identifier
    """
    logger.info("EXPORT_RETRIEVED: export_id=%s", export_id)


def log_export_verified(export_id: str, all_ok: bool) -> None:
    """Log export verification action.

    Args:
        export_id: Export identifier
        all_ok: Whether all verification checks passed
    """
    logger.info("EXPORT_VERIFIED: export_id=%s, all_ok=%s", export_id, all_ok)
