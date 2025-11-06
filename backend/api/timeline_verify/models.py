"""Pydantic models for timeline verify API.

Defines request/response models for hash verification functionality.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class VerifyHashItem(BaseModel):
    """Single hash verification request."""

    target_id: str = Field(..., description="Session ID or event ID to verify")
    expected_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Expected SHA256 hash (64 hex chars)",
    )


class VerifyHashRequest(BaseModel):
    """Batch hash verification request."""

    items: list[VerifyHashItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Hashes to verify",
    )
    verbose: bool = Field(default=False, description="Include detailed verification info")


class VerifyHashDetail(BaseModel):
    """Hash verification result for single item."""

    target_id: str
    valid: bool
    computed_hash: str
    expected_hash: str
    match: bool
    error: Optional[str] = None


class VerifyHashResponse(BaseModel):
    """Batch hash verification response."""

    timestamp: str
    all_valid: bool
    items: list[VerifyHashDetail]
    summary: dict[str, Any] = Field(
        default_factory=dict, description="Stats: total, valid, invalid, duration_ms"
    )
