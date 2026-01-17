"""System information endpoints.

Disk usage and system management operations.
Public API - accessible to authenticated users.

Author: Bernard Uriza Orozco
Created: 2025-12-11
"""

from __future__ import annotations

import shutil
import time
from datetime import UTC, datetime, timezone
from typing import Any

import httpx
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_model_catalog.services.tunnel_url_provider import (
    get_tunnel_url_provider,
)
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pathlib import Path
from pydantic import BaseModel, Field

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


class LLMStatusResponse(BaseModel):
    """LLM/Ollama connection status with detailed info."""

    status: str = Field(..., description="online | offline | checking")
    url: str = Field(..., description="Current Ollama URL being used")
    is_tunnel: bool = Field(..., description="True if using Cloudflare tunnel")
    tunnel_info: dict[str, Any] | None = Field(
        None, description="Tunnel details (hostname, updated_at) if available"
    )
    models: list[str] = Field(default_factory=list, description="Available models")
    latency_ms: int | None = Field(None, description="Response latency in ms")
    last_check: str = Field(..., description="ISO timestamp of this check")
    priority: str = Field(
        ..., description="Current priority: 'tunnel' or 'local_fallback'"
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/disk-usage", response_model=DiskUsageResponse)
async def get_disk_usage() -> DiskUsageResponse:
    """Get disk usage for storage directory.

    Returns:
        Disk usage statistics
    """
    try:
        # Get storage directory path
        storage_path = Path("storage")
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)

        # Calculate directory size
        total_size = sum(f.stat().st_size for f in storage_path.rglob("*") if f.is_file())

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
            used_bytes=total_size,
            total_bytes=disk_stat.total,
            percent=percent,
        )

        return DiskUsageResponse(used=used, total=total, percent=round(percent, 2))

    except Exception as e:
        logger.error("DISK_USAGE_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get disk usage")


@router.post("/clear-memory")
async def clear_longitudinal_memory(
    user_id: str = Query(..., description="User ID (Auth0 sub) for audit logging"),
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
        user_id: User identifier for audit logging

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
                logger.info("SESSION_FILE_DELETED", file=str(h5_file), user_id=user_id)

        # Delete session metadata
        data_sessions_path = Path("data/sessions")
        if data_sessions_path.exists():
            for session_dir in data_sessions_path.iterdir():
                if session_dir.is_dir():
                    shutil.rmtree(session_dir)
                    deleted_files += 1
                    logger.info("SESSION_DIR_DELETED", dir=str(session_dir), user_id=user_id)

        # Delete chat message cache (if exists)
        chat_cache_path = Path("data/llm_cache")
        if chat_cache_path.exists():
            for cache_file in chat_cache_path.glob("*"):
                if cache_file.is_file():
                    cache_file.unlink()
                    deleted_files += 1

        logger.warning(
            "LONGITUDINAL_MEMORY_CLEARED",
            user_id=user_id,
            files_deleted=deleted_files,
        )

        return {
            "message": f"Memoria longitudinal eliminada exitosamente. {deleted_files} archivos eliminados.",
            "files_deleted": str(deleted_files),
        }

    except Exception as e:
        logger.error("CLEAR_MEMORY_FAILED", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to clear memory: {e!s}")


@router.get("/llm-status", response_model=LLMStatusResponse)
async def get_llm_status() -> LLMStatusResponse:
    """Get detailed LLM/Ollama connection status.

    Returns comprehensive information about the current LLM connection:
    - Connection status (online/offline)
    - Active URL (tunnel or localhost fallback)
    - Tunnel info (hostname, last update) if using tunnel
    - Available models
    - Response latency

    Returns:
        LLMStatusResponse with detailed connection info
    """
    provider = get_tunnel_url_provider()

    # Get current URL (triggers cache refresh if needed)
    start_time = time.time()
    current_url = await provider.get_ollama_url()
    tunnel_info = await provider.get_tunnel_info()

    # Determine if using tunnel
    is_tunnel = tunnel_info is not None and "tunnel_url" in (tunnel_info or {})
    fallback_url = "http://localhost:11434"

    # Check if Ollama is actually reachable and get models
    status = "offline"
    models: list[str] = []
    latency_ms: int | None = None

    try:
        async with httpx.AsyncClient() as client:
            check_start = time.time()
            response = await client.get(f"{current_url}/api/tags", timeout=2.0)
            latency_ms = int((time.time() - check_start) * 1000)

            if response.status_code == 200:
                status = "online"
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
    except Exception as e:
        logger.debug("LLM_STATUS_CHECK_FAILED", error=str(e), url=current_url)
        status = "offline"

    priority = "tunnel" if is_tunnel and current_url != fallback_url else "local_fallback"

    logger.info(
        "LLM_STATUS_CHECKED",
        status=status,
        url=current_url,
        is_tunnel=is_tunnel,
        models_count=len(models),
        latency_ms=latency_ms,
    )

    return LLMStatusResponse(
        status=status,
        url=current_url,
        is_tunnel=is_tunnel,
        tunnel_info=tunnel_info,
        models=models,
        latency_ms=latency_ms,
        last_check=datetime.now(UTC).isoformat(),
        priority=priority,
    )
