"""System information endpoints.

Disk usage and system management operations.
Public API - accessible to authenticated users.

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.jwt import get_current_user
from backend.logger import get_logger
from backend.schemas import User

logger = get_logger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class DiskUsageResponse(BaseModel):
    """Disk usage information."""

    used: str  # Human-readable (e.g., "2.5 GB")
    total: str  # Human-readable (e.g., "100 GB")
    percent: float  # Percentage used (0-100)


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/disk-usage", response_model=DiskUsageResponse)
async def get_disk_usage(user: User = Depends(get_current_user)) -> DiskUsageResponse:
    """Get disk usage for storage directory.

    Args:
        user: Authenticated user (injected)

    Returns:
        Disk usage statistics
    """
    try:
        # Get storage directory path
        storage_path = Path("storage")
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)

        # Calculate directory size
        total_size = sum(
            f.stat().st_size for f in storage_path.rglob("*") if f.is_file()
        )

        # Get disk usage for the mount point
        disk_stat = shutil.disk_usage(storage_path)

        # Convert to human-readable
        def format_bytes(bytes_val: int) -> str:
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} PB"

        used = format_bytes(total_size)
        total = format_bytes(disk_stat.total)
        percent = (total_size / disk_stat.total * 100) if disk_stat.total > 0 else 0

        logger.info(
            "DISK_USAGE_RETRIEVED",
            user_id=user.sub,
            used_bytes=total_size,
            total_bytes=disk_stat.total,
            percent=percent,
        )

        return DiskUsageResponse(used=used, total=total, percent=round(percent, 2))

    except Exception as e:
        logger.error("DISK_USAGE_FAILED", error=str(e), user_id=user.sub)
        raise HTTPException(status_code=500, detail="Failed to get disk usage")


@router.post("/clear-memory")
async def clear_longitudinal_memory(
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Clear all longitudinal memory (HDF5 sessions and chat messages).

    Deletes:
    - storage/sessions/*.h5 (HDF5 session files)
    - data/sessions/* (session metadata)
    - Chat message history

    Preserves:
    - Persona configurations
    - Patient records
    - Provider data

    Args:
        user: Authenticated user (injected)

    Returns:
        Success message with deletion count
    """
    try:
        deleted_files = 0

        # Delete HDF5 session files
        sessions_path = Path("storage/sessions")
        if sessions_path.exists():
            for h5_file in sessions_path.glob("*.h5"):
                h5_file.unlink()
                deleted_files += 1
                logger.info("SESSION_FILE_DELETED", file=str(h5_file), user_id=user.sub)

        # Delete session metadata
        data_sessions_path = Path("data/sessions")
        if data_sessions_path.exists():
            for session_dir in data_sessions_path.iterdir():
                if session_dir.is_dir():
                    shutil.rmtree(session_dir)
                    deleted_files += 1
                    logger.info(
                        "SESSION_DIR_DELETED", dir=str(session_dir), user_id=user.sub
                    )

        # Delete chat message cache (if exists)
        chat_cache_path = Path("data/llm_cache")
        if chat_cache_path.exists():
            for cache_file in chat_cache_path.glob("*"):
                if cache_file.is_file():
                    cache_file.unlink()
                    deleted_files += 1

        logger.warning(
            "LONGITUDINAL_MEMORY_CLEARED",
            user_id=user.sub,
            files_deleted=deleted_files,
        )

        return {
            "message": f"Memoria longitudinal eliminada exitosamente. {deleted_files} archivos eliminados.",
            "files_deleted": str(deleted_files),
        }

    except Exception as e:
        logger.error("CLEAR_MEMORY_FAILED", error=str(e), user_id=user.sub)
        raise HTTPException(status_code=500, detail=f"Failed to clear memory: {e!s}")
