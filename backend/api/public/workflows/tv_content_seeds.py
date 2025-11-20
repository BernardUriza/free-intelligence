"""
TV Content Seeds Management - AURITY

Manages FI default content seeds (widgets, tips, philosophy) that can be:
- Loaded as defaults for all clinics
- Overridden/customized by individual clinics
- Activated/deactivated by doctors

This replaces hardcoded DEFAULT_CONTENT in FIAvatar.tsx with editable seeds.

Architecture:
  - Seeds stored as JSON files in storage/tv_seeds/
  - Doctor can edit/disable any seed
  - Backward compatible with existing clinic_media.py

Card: FI-TV-REFAC-001

Author: Bernard Uriza Orozco
Created: 2025-11-18
"""

import json
import time
from pathlib import Path
from typing import Any, List, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Storage configuration
SEEDS_STORAGE_PATH = Path("storage/tv_seeds")
SEEDS_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Seed metadata file (tracks which seeds are active/disabled per clinic)
SEED_METADATA_FILE = SEEDS_STORAGE_PATH / "seed_metadata.json"


# ============================================================================
# Request/Response Schemas
# ============================================================================


class TVContentSeed(BaseModel):
    """
    Unified TV content schema for both FI seeds and doctor content.

    This replaces the hardcoded DEFAULT_CONTENT array in FIAvatar.tsx.
    """

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
    widget_data: dict[str, Any] | None = Field(None, description="Widget-specific data (JSON)")

    # Seed management
    is_system_default: bool = Field(
        default=True, description="True if FI seed, False if doctor-created"
    )
    is_active: bool = Field(default=True, description="Whether content is active in carousel")
    display_order: int = Field(default=0, description="Display order (0-indexed)")

    # Metadata
    clinic_id: str | None = Field(None, description="Clinic ID (None = global seed)")
    created_at: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Creation timestamp (ms)",
    )
    updated_at: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Last update timestamp (ms)",
    )


class TVContentListResponse(BaseModel):
    """Response for unified content list (seeds + doctor content)."""

    total: int
    content: List[TVContentSeed]


class SeedMetadata(BaseModel):
    """Per-clinic metadata for seed activation status."""

    clinic_id: str
    disabled_seeds: List[str] = Field(default_factory=list, description="List of disabled seed IDs")
    custom_order: List[str] | None = Field(
        default=None, description="Custom display order (content_ids)"
    )


# ============================================================================
# Storage Helper Functions
# ============================================================================


def save_seed(seed: TVContentSeed) -> None:
    """Save TV content seed to JSON file."""
    seed_file = SEEDS_STORAGE_PATH / f"{seed.content_id}.json"
    with open(seed_file, "w", encoding="utf-8") as f:
        json.dump(seed.model_dump(), f, indent=2, ensure_ascii=False)


def load_seed(content_id: str) -> TVContentSeed | None:
    """Load TV content seed from JSON file."""
    seed_file = SEEDS_STORAGE_PATH / f"{content_id}.json"
    if not seed_file.exists():
        return None

    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)
        return TVContentSeed(**data)


def load_all_seeds() -> List[TVContentSeed]:
    """Load all TV content seeds."""
    seeds = []
    for seed_file in SEEDS_STORAGE_PATH.glob("*.json"):
        # Skip metadata file
        if seed_file.name == "seed_metadata.json":
            continue

        with open(seed_file, encoding="utf-8") as f:
            data = json.load(f)
            seeds.append(TVContentSeed(**data))

    # Sort by display_order
    seeds.sort(key=lambda s: s.display_order)
    return seeds


def load_seed_metadata(clinic_id: str) -> SeedMetadata:
    """Load seed metadata for a clinic (which seeds are disabled)."""
    if not SEED_METADATA_FILE.exists():
        return SeedMetadata(clinic_id=clinic_id)

    with open(SEED_METADATA_FILE, encoding="utf-8") as f:
        all_metadata = json.load(f)

    clinic_metadata = all_metadata.get(clinic_id)
    if not clinic_metadata:
        return SeedMetadata(clinic_id=clinic_id)

    return SeedMetadata(**clinic_metadata)


def save_seed_metadata(metadata: SeedMetadata) -> None:
    """Save seed metadata for a clinic."""
    # Load all metadata
    all_metadata = {}
    if SEED_METADATA_FILE.exists():
        with open(SEED_METADATA_FILE, encoding="utf-8") as f:
            all_metadata = json.load(f)

    # Update clinic metadata
    all_metadata[metadata.clinic_id] = metadata.model_dump()

    # Save
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
    description="""
    Returns unified TV content combining:
    - FI default seeds (editable by doctor)
    - Doctor-uploaded media (images/videos/messages)

    Replaces separate /clinic-media/list + hardcoded DEFAULT_CONTENT.

    **Card**: FI-TV-REFAC-001
    """,
)
async def list_tv_content(
    clinic_id: str | None = None,
    active_only: bool = True,
    include_doctor_media: bool = True,
) -> TVContentListResponse:
    """
    List all TV content for carousel display.

    This is the SINGLE SOURCE OF TRUTH for FIAvatar carousel.
    No more hardcoded DEFAULT_CONTENT!
    """
    try:
        content_list: List[TVContentSeed] = []

        # 1. Load FI seeds
        seeds = load_all_seeds()

        # 2. Apply clinic-specific overrides (disabled seeds)
        if clinic_id:
            metadata = load_seed_metadata(clinic_id)
            seeds = [s for s in seeds if s.content_id not in metadata.disabled_seeds]

        # 3. Filter by active status
        if active_only:
            seeds = [s for s in seeds if s.is_active]

        content_list.extend(seeds)

        # 4. TODO: Merge with doctor-uploaded media from clinic_media.py
        # This will be implemented when we unify the schemas
        # For now, frontend still appends clinic slides separately

        logger.info(
            "Listed TV content",
            total_seeds=len(seeds),
            clinic_id=clinic_id,
            active_only=active_only,
        )

        return TVContentListResponse(total=len(content_list), content=content_list)

    except Exception as e:
        logger.error("Failed to list TV content", error=str(e), exc_info=True)
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
) -> TVContentSeed:
    """
    Update TV content metadata.

    Doctors can:
    - Edit FI seed text/duration
    - Activate/deactivate seeds
    - Reorder content
    """
    try:
        seed = load_seed(content_id)
        if not seed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content {content_id} not found",
            )

        # Update allowed fields
        for key, value in updates.items():
            if hasattr(seed, key):
                setattr(seed, key, value)

        seed.updated_at = int(time.time() * 1000)
        save_seed(seed)

        logger.info("Updated TV content", content_id=content_id, updates=updates)
        return seed

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update TV content", error=str(e), exc_info=True)
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
) -> dict:
    """
    Disable a FI default seed for a specific clinic.

    The seed remains available globally but won't show for this clinic.
    """
    try:
        # Verify seed exists
        seed = load_seed(content_id)
        if not seed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Seed {content_id} not found",
            )

        # Load clinic metadata
        metadata = load_seed_metadata(clinic_id)

        # Add to disabled list
        if content_id not in metadata.disabled_seeds:
            metadata.disabled_seeds.append(content_id)
            save_seed_metadata(metadata)

        logger.info("Disabled seed for clinic", clinic_id=clinic_id, content_id=content_id)

        return {
            "success": True,
            "message": f"Seed {content_id} disabled for clinic {clinic_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to disable seed", error=str(e), exc_info=True)
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
) -> dict:
    """
    Re-enable a previously disabled FI seed for a clinic.
    """
    try:
        # Load clinic metadata
        metadata = load_seed_metadata(clinic_id)

        # Remove from disabled list
        if content_id in metadata.disabled_seeds:
            metadata.disabled_seeds.remove(content_id)
            save_seed_metadata(metadata)

        logger.info("Enabled seed for clinic", clinic_id=clinic_id, content_id=content_id)

        return {
            "success": True,
            "message": f"Seed {content_id} enabled for clinic {clinic_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to enable seed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable seed: {e!s}",
        )
