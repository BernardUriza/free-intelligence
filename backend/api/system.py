from __future__ import annotations

"""
System Health API - Unified health checks for all services

Card: FI-UI-FEAT-206 (Diarization Progress + Health + Path Hardening)
File: backend/api/system.py
Created: 2025-10-30

Endpoints:
  GET /api/system/health - Unified health check aggregating all services

Clean Code Architecture:
- Thin controller delegates all health check logic to SystemHealthService
- Service layer encapsulates backend, diarization, LLM, policy checks
- Endpoint focuses only on HTTP response formatting
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system")


class SystemHealthResponse(BaseModel):
    """Unified system health response"""

    ok: bool
    services: dict[str, Any]
    version: str
    time: str


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health() -> SystemHealthResponse:
    """
    Unified health check aggregating all services.

    Delegates all health check logic to SystemHealthService.

    Response shape:
    {
      "ok": true,
      "services": {
        "backend": true,
        "diarization": { "whisper": true, "ffmpeg": true },
        "llm": { "ollama": true, "models": ["qwen2.5:7b-instruct-q4_0"] },
        "policy": true
      },
      "version": "v0.3.x",
      "time": "<ISO8601>"
    }

    Returns:
        SystemHealthResponse with ok=True only if critical services are healthy
    """
    try:
        container = get_container()
        health_service = container.get_system_health_service()
        health_data = health_service.get_system_health()

        logger.info("SYSTEM_HEALTH_RETRIEVED", ok=health_data["ok"])

        return SystemHealthResponse(
            ok=health_data["ok"],
            services=health_data["services"],
            version="v0.3.0",
            time=datetime.now(UTC).isoformat() + "Z",
        )
    except Exception as e:
        logger.error(f"SYSTEM_HEALTH_FAILED: {str(e)}")
        # Return degraded response on error
        return SystemHealthResponse(
            ok=False,
            services={"error": str(e)},
            version="v0.3.0",
            time=datetime.now(UTC).isoformat() + "Z",
        )
