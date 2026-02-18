"""System Health API.

System health check aggregator

File: backend/api/system/router.py
Reorganized: 2025-11-08 (moved from backend/api/system.py)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.system.system_health_service import DISystemHealthService
from backend.utils.common.logging.logger import get_logger
from backend.infrastructure.system.api.public.system.dependencies import get_system_health_service
from fastapi import APIRouter, Depends
from pydantic import BaseModel

logger = get_logger(__name__)

router = APIRouter()


class SystemHealthResponse(BaseModel):
    """Unified system health response"""

    ok: bool
    services: dict[str, Any]
    version: str
    time: str


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    health_service: DISystemHealthService = Depends(get_system_health_service),
) -> SystemHealthResponse:
    """
    Unified health check aggregating all services.

    Delegates all health check logic to SystemHealthService.

    Response shape:
    {
      "ok": true,
      "services": {
        "backend": true,
        "diarization": { "whisper": true, "ffmpeg": true },
        "llm": { "ollama": true, "models": ["qwen3:1.7b"] },
        "policy": true
      },
      "version": "v0.3.x",
      "time": "<ISO8601>"
    }

    Args:
        health_service: Injected system health service

    Returns:
        SystemHealthResponse with ok=True only if critical services are healthy
    """
    try:
        health_data = health_service.get_system_health()

        logger.info("SYSTEM_HEALTH_RETRIEVED", ok=health_data["ok"])

        return SystemHealthResponse(
            ok=health_data["ok"],
            services=health_data["services"],
            version="v0.3.0",
            time=datetime.now(UTC).isoformat() + "Z",
        )
    except Exception as e:
        logger.error(f"SYSTEM_HEALTH_FAILED: {e!s}")
        # Return degraded response on error
        return SystemHealthResponse(
            ok=False,
            services={"error": str(e)},
            version="v0.3.0",
            time=datetime.now(UTC).isoformat() + "Z",
        )
