from __future__ import annotations

"""
FI Diagnostics API Router
Card: FI-INFRA-STR-014

Endpoints para health checks y diagnósticos del sistema.

Clean Code Architecture:
- Thin controllers delegate all diagnostics logic to DiagnosticsService
- Service layer encapsulates system probes (Python, storage, corpus, Node.js, pnpm, PM2)
- Endpoints focus only on HTTP response formatting
"""

import os
from datetime import UTC, datetime
from typing import Any, Optional

UTC = UTC

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response."""

    status: str = Field(..., description="Overall status: healthy, degraded, unhealthy")
    timestamp: str = Field(..., description="Timestamp of health check")
    checks: dict[str, dict] = Field(..., description="Individual health checks")
    version: str = Field(..., description="System version")


class ServiceStatus(BaseModel):
    """Service status response."""

    service: str
    status: str
    pid: Optional[int]
    uptime_seconds: Optional[int]
    memory_mb: Optional[float]


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Comprehensive health check endpoint.

    Delegates all diagnostics logic to DiagnosticsService.

    Returns:
        HealthStatus with all subsystem checks
    """
    try:
        container = get_container()
        diag_service = container.get_diagnostics_service()
        diag_data = diag_service.get_diagnostics()

        logger.info("DIAGNOSTICS_HEALTH_RETRIEVED", status=diag_data["status"])

        return HealthStatus(
            status=diag_data["status"],
            timestamp=datetime.now(UTC).isoformat() + "Z",
            checks=diag_data["checks"],
            version="0.1.0",
        )
    except Exception as e:
        logger.error(f"DIAGNOSTICS_HEALTH_FAILED: {e!s}")
        # Return degraded response on error with empty checks
        return HealthStatus(
            status="degraded",
            timestamp=datetime.now(UTC).isoformat() + "Z",
            checks={},
            version="0.1.0",
        )


@router.get("/services", response_model=list[ServiceStatus])
async def service_status() -> list[ServiceStatus]:
    """
    Get status of all PM2-managed services.

    Delegates to DiagnosticsService for PM2/lsof checks.

    Returns:
        List of ServiceStatus for each service
    """
    try:
        container = get_container()
        diag_service = container.get_diagnostics_service()
        pm2_data = diag_service.check_pm2()

        services = []
        for service_info in pm2_data.get("services", []):
            services.append(
                ServiceStatus(
                    service=service_info.get("name", "unknown"),
                    status=service_info.get("status", "unknown"),
                    pid=service_info.get("pid"),
                    uptime_seconds=service_info.get("uptime"),
                    memory_mb=service_info.get("memory_mb"),
                )
            )

        logger.info("SERVICE_STATUS_RETRIEVED", count=len(services))
        return services
    except Exception as e:
        logger.error(f"SERVICE_STATUS_FAILED: {e!s}")
        return []


@router.get("/system")
async def system_info() -> dict[str, Any]:
    """
    Get system information.

    Delegates to DiagnosticsService for system info gathering.

    Returns:
        Dict with system specs, disk usage, etc.
    """
    try:
        container = get_container()
        diag_service = container.get_diagnostics_service()
        system_data = diag_service.get_system_info()

        logger.info("SYSTEM_INFO_RETRIEVED", os=system_data.get("os"))
        return system_data
    except Exception as e:
        logger.error(f"SYSTEM_INFO_FAILED: {e!s}")
        return {"error": str(e)}


@router.get("/readiness")
async def readiness_check() -> dict[str, Any]:
    """
    Readiness probe for Kubernetes/PM2.

    Delegates to DiagnosticsService for readiness verification.

    Returns:
        200 if service is ready, with ready status
    """
    try:
        container = get_container()
        diag_service = container.get_diagnostics_service()
        is_ready = diag_service.check_readiness()

        logger.info("READINESS_CHECK_COMPLETED", ready=is_ready)
        return {
            "ready": is_ready,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"READINESS_CHECK_FAILED: {e!s}")
        return {"ready": False, "error": str(e)}


@router.get("/liveness")
async def liveness_check() -> dict[str, Any]:
    """
    Liveness probe for Kubernetes/PM2.

    Delegates to DiagnosticsService for liveness verification.
    Always returns 200 if process is running.

    Returns:
        Liveness status with timestamp and PID
    """
    try:
        container = get_container()
        diag_service = container.get_diagnostics_service()
        is_alive = diag_service.check_liveness()

        logger.info("LIVENESS_CHECK_COMPLETED", alive=is_alive)
        return {
            "alive": is_alive,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "pid": os.getpid(),
        }
    except Exception as e:
        logger.error(f"LIVENESS_CHECK_FAILED: {e!s}")
        return {"alive": False, "error": str(e)}
