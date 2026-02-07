"""TV Content Seeds Management - AURITY.

Manages FI default content seeds (widgets, tips, philosophy) that can be:
- Loaded as defaults for all clinics
- Overridden/customized by individual clinics
- Activated/deactivated by doctors

Endpoints (4 total):
- GET   /tv-content/list - List all TV content (seeds + doctor content)
- PATCH /tv-content/{id} - Update TV content
- POST  /tv-content/disable-seed - Disable seed for clinic
- POST  /tv-content/enable-seed - Re-enable seed for clinic

Card: FI-TV-REFAC-001

Author: Bernard Uriza Orozco
Created: 2025-11-18
Migrated: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user
from backend.infrastructure.auth.domain.entities.user import User
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Storage configuration
SEEDS_STORAGE_PATH = Path("storage/tv_seeds")
SEEDS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
SEED_METADATA_FILE = SEEDS_STORAGE_PATH / "seed_metadata.json"


# ============================================================================
# Models
# ============================================================================


class TVContentSeed(BaseModel):
    """Unified TV content schema for FI seeds and doctor content."""

    content_id: str = Field(..., description="Unique content identifier")
    type: Literal["welcome", "tip", "metric", "philosophy", "doctor_message", "widget"] = Field(
        ..., description="Content type"
    )
    content: str = Field(default="", description="Text content (empty for widgets)")
    duration: int = Field(default=15000, description="Display duration in milliseconds")

    # Widget-specific fields
    widget_type: (
        Literal[
            "weather",
            "trivia",
            "breathing",
            "daily_tip",
            "calming",
            "clinic_image",
            "clinic_video",
            "clinic_message",
        ]
        | None
    ) = Field(None, description="Widget type if type='widget'")
    widget_data: dict[str, Any] | None = Field(None, description="Widget-specific data")

    # Seed management
    is_system_default: bool = Field(default=True, description="True if FI seed")
    is_active: bool = Field(default=True, description="Whether content is active")
    display_order: int = Field(default=0, description="Display order (0-indexed)")

    # Metadata
    clinic_id: str | None = Field(None, description="Clinic ID (None = global)")
    created_at: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Creation timestamp (ms)",
    )
    updated_at: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Last update timestamp (ms)",
    )


class TVContentListResponse(BaseModel):
    """Response for unified content list."""

    total: int
    content: list[TVContentSeed]


class SeedMetadata(BaseModel):
    """Per-clinic metadata for seed activation status."""

    clinic_id: str
    disabled_seeds: list[str] = Field(default_factory=list)
    custom_order: list[str] | None = Field(default=None)


# ============================================================================
# Storage Helpers
# ============================================================================


def _save_seed(seed: TVContentSeed) -> None:
    """Save TV content seed to JSON file."""
    seed_file = SEEDS_STORAGE_PATH / f"{seed.content_id}.json"
    with open(seed_file, "w", encoding="utf-8") as f:
        json.dump(seed.model_dump(), f, indent=2, ensure_ascii=False)


def _load_seed(content_id: str) -> TVContentSeed | None:
    """Load TV content seed from JSON file."""
    seed_file = SEEDS_STORAGE_PATH / f"{content_id}.json"
    if not seed_file.exists():
        return None

    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)
        return TVContentSeed(**data)


def _load_all_seeds() -> list[TVContentSeed]:
    """Load all TV content seeds."""
    seeds = []
    for seed_file in SEEDS_STORAGE_PATH.glob("*.json"):
        if seed_file.name == "seed_metadata.json":
            continue

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)
            seeds.append(TVContentSeed(**data))

    seeds.sort(key=lambda s: s.display_order)
    return seeds


def _load_seed_metadata(clinic_id: str) -> SeedMetadata:
    """Load seed metadata for a clinic."""
    if not SEED_METADATA_FILE.exists():
        return SeedMetadata(clinic_id=clinic_id)

    with open(SEED_METADATA_FILE, encoding="utf-8") as f:
        all_metadata = json.load(f)

    clinic_metadata = all_metadata.get(clinic_id)
    if not clinic_metadata:
        return SeedMetadata(clinic_id=clinic_id)

    return SeedMetadata(**clinic_metadata)


def _save_seed_metadata(metadata: SeedMetadata) -> None:
    """Save seed metadata for a clinic."""
    all_metadata = {}
    if SEED_METADATA_FILE.exists():
        with open(SEED_METADATA_FILE, encoding="utf-8") as f:
            all_metadata = json.load(f)

    all_metadata[metadata.clinic_id] = metadata.model_dump()

    with open(SEED_METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/tv-content/list",
    response_model=TVContentListResponse,
    tags=["TV Content"],
    summary="List all TV content (seeds + doctor content)",
)
async def list_tv_content(
    clinic_id: str | None = None,
    active_only: bool = True,
    include_doctor_media: bool = True,
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> TVContentListResponse:
    """List all TV content for carousel display.

    Single source of truth for FIAvatar carousel.
    """
    try:
        content_list: list[TVContentSeed] = []

        # Load FI seeds
        seeds = _load_all_seeds()

        # Apply clinic-specific overrides
        if clinic_id:
            metadata = _load_seed_metadata(clinic_id)
            seeds = [s for s in seeds if s.content_id not in metadata.disabled_seeds]

        # Filter by active status
        if active_only:
            seeds = [s for s in seeds if s.is_active]

        content_list.extend(seeds)

        logger.info(
            "Listed TV content",
            total_seeds=len(seeds),
            clinic_id=clinic_id,
            active_only=active_only,
        )

        return TVContentListResponse(total=len(content_list), content=content_list)

    except Exception as e:
        audit_service.log_action(
            action="tv_content_list_failed",
            user_id=current_user.id,
            clinic_id=clinic_id,
            resource="tv_content",
            result="failure",
            details={"error": str(e), "active_only": active_only},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list TV content: {e!s}",
        )


@router.patch(
    "/tv-content/{content_id}",
    response_model=TVContentSeed,
    tags=["TV Content"],
    summary="Update TV content (seed or doctor content)",
)
async def update_tv_content(
    content_id: str,
    updates: dict[str, Any],
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> TVContentSeed:
    """Update TV content metadata.

    Doctors can edit FI seed text/duration, activate/deactivate, reorder.
    """
    try:
        seed = _load_seed(content_id)
        if not seed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content {content_id} not found",
            )

        for key, value in updates.items():
            if hasattr(seed, key):
                setattr(seed, key, value)

        seed.updated_at = int(time.time() * 1000)
        _save_seed(seed)

        logger.info("Updated TV content", content_id=content_id, updates=updates)
        return seed

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="tv_content_update_failed",
            user_id=current_user.id,
            resource=f"tv_content:{content_id}",
            result="failure",
            details={"error": str(e), "updates": updates},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update content: {e!s}",
        )


@router.post(
    "/tv-content/disable-seed",
    tags=["TV Content"],
    summary="Disable a FI seed for a specific clinic",
)
async def disable_seed_for_clinic(
    clinic_id: str,
    content_id: str,
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Disable a FI default seed for a specific clinic."""
    try:
        seed = _load_seed(content_id)
        if not seed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seed {content_id} not found",
            )

        metadata = _load_seed_metadata(clinic_id)

        if content_id not in metadata.disabled_seeds:
            metadata.disabled_seeds.append(content_id)
            _save_seed_metadata(metadata)

        logger.info("Disabled seed for clinic", clinic_id=clinic_id, content_id=content_id)

        return {
            "success": True,
            "message": f"Seed {content_id} disabled for clinic {clinic_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="tv_seed_disable_failed",
            user_id=current_user.id,
            clinic_id=clinic_id,
            resource=f"seed:{content_id}",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable seed: {e!s}",
        )


@router.post(
    "/tv-content/enable-seed",
    tags=["TV Content"],
    summary="Re-enable a FI seed for a specific clinic",
)
async def enable_seed_for_clinic(
    clinic_id: str,
    content_id: str,
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Re-enable a previously disabled FI seed for a clinic."""
    try:
        metadata = _load_seed_metadata(clinic_id)

        if content_id in metadata.disabled_seeds:
            metadata.disabled_seeds.remove(content_id)
            _save_seed_metadata(metadata)

        logger.info("Enabled seed for clinic", clinic_id=clinic_id, content_id=content_id)

        return {
            "success": True,
            "message": f"Seed {content_id} enabled for clinic {clinic_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="tv_seed_enable_failed",
            user_id=current_user.id,
            clinic_id=clinic_id,
            resource=f"seed:{content_id}",
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable seed: {e!s}",
        )
