"""Pydantic models for export API.

Defines request/response models for session export functionality.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


def _default_verify_targets() -> list[Literal["md", "json", "manifest"]]:
    """Default verification targets for VerifyRequest.

    Returns list of all export formats for verification.
    """
    return ["md", "json", "manifest"]


class ExportInclude(BaseModel):  # type: ignore[misc]
    """What to include in export."""

    transcript: bool = True
    events: bool = True
    attachments: bool = False


class ExportRequest(BaseModel):  # type: ignore[misc]
    """Create export request."""

    session_id: str
    formats: list[Literal["md", "json"]] = Field(..., min_length=1)
    include: ExportInclude = Field(default_factory=ExportInclude)


class ExportArtifact(BaseModel):  # type: ignore[misc]
    """Export artifact metadata."""

    format: Literal["md", "json", "manifest"]  # noqa: A003
    url: str
    sha256: str
    bytes: int  # noqa: A003


class ExportResponse(BaseModel):  # type: ignore[misc]
    """Export response."""

    export_id: str
    status: Literal["ready", "processing"]
    artifacts: list[ExportArtifact]
    manifest_url: str


class VerifyRequest(BaseModel):  # type: ignore[misc]
    """Verify request."""

    targets: list[Literal["md", "json", "manifest"]] = Field(
        default_factory=_default_verify_targets
    )


class VerifyResult(BaseModel):  # type: ignore[misc]
    """Verify result for single target."""

    target: str
    ok: bool
    message: Optional[str] = None


class VerifyResponse(BaseModel):  # type: ignore[misc]
    """Verify response."""

    ok: bool
    results: list[VerifyResult]
