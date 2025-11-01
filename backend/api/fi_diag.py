from __future__ import annotations

"""
FI Diagnostics API Router
Card: FI-INFRA-STR-014

Endpoints para health checks y diagnósticos del sistema.
"""
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/diag")


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
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns:
        HealthStatus with all subsystem checks
    """
    checks = {}

    # Check 1: Python runtime
    checks["python"] = {
        "status": "healthy",
        "version": sys.version.split()[0],
        "executable": sys.executable,
    }

    # Check 2: Storage directories
    storage_path = Path("storage")
    data_path = Path("data")

    checks["storage"] = {
        "status": "healthy" if storage_path.exists() else "degraded",
        "path": str(storage_path.absolute()),
        "writable": os.access(storage_path.parent, os.W_OK),
    }

    checks["data"] = {
        "status": "healthy" if data_path.exists() else "degraded",
        "path": str(data_path.absolute()),
        "writable": os.access(data_path.parent, os.W_OK),
    }

    # Check 3: HDF5 corpus
    corpus_path = Path("storage/corpus.h5")
    checks["corpus"] = {
        "status": "healthy" if corpus_path.exists() else "warning",
        "exists": corpus_path.exists(),
        "size_mb": round(corpus_path.stat().st_size / 1024 / 1024, 2)
        if corpus_path.exists()
        else 0,
    }

    # Check 4: Node.js (for frontend)
    try:
        node_result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=2
        )
        checks["nodejs"] = {
            "status": "healthy" if node_result.returncode == 0 else "unhealthy",
            "version": node_result.stdout.strip() if node_result.returncode == 0 else None,
        }
    except Exception as e:
        checks["nodejs"] = {"status": "unhealthy", "error": str(e)}

    # Check 5: pnpm
    try:
        pnpm_result = subprocess.run(
            ["pnpm", "--version"], capture_output=True, text=True, timeout=2
        )
        checks["pnpm"] = {
            "status": "healthy" if pnpm_result.returncode == 0 else "unhealthy",
            "version": pnpm_result.stdout.strip() if pnpm_result.returncode == 0 else None,
        }
    except Exception as e:
        checks["pnpm"] = {"status": "unhealthy", "error": str(e)}

    # Check 6: PM2 (if installed)
    try:
        pm2_result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=2)
        checks["pm2"] = {
            "status": "healthy" if pm2_result.returncode == 0 else "warning",
            "installed": pm2_result.returncode == 0,
        }
    except FileNotFoundError:
        checks["pm2"] = {"status": "warning", "installed": False}
    except Exception as e:
        checks["pm2"] = {"status": "warning", "error": str(e)}

    # Determine overall status
    statuses = [check["status"] for check in checks.values()]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat() + "Z",
        checks=checks,
        version="0.1.0",
    )


@router.get("/services", response_model=list[ServiceStatus])
async def service_status():
    """
    Get status of all PM2-managed services.

    Returns:
        List of ServiceStatus for each service
    """
    services = []

    try:
        # Try to get PM2 process list
        result = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            import json

            processes = json.loads(result.stdout)

            for proc in processes:
                services.append(
                    ServiceStatus(
                        service=proc.get("name", "unknown"),
                        status=proc.get("pm2_env", {}).get("status", "unknown"),
                        pid=proc.get("pid"),
                        uptime_seconds=proc.get("pm2_env", {}).get("pm_uptime"),
                        memory_mb=round(proc.get("monit", {}).get("memory", 0) / 1024 / 1024, 2)
                        if proc.get("monit")
                        else None,
                    )
                )
        else:
            logger.warning("PM2 not available or no processes running")

    except FileNotFoundError:
        logger.warning("PM2 not installed")
    except Exception as e:
        logger.error(f"Error getting service status: {e}")

    # If no PM2 processes, check ports directly
    if not services:
        port_services = {
            "fi-backend-api": 7001,
            "fi-timeline-api": 9002,
            "fi-frontend": 9000,
        }

        for service_name, port in port_services.items():
            result = subprocess.run(["lsof", f"-ti:{port}"], capture_output=True)
            status = "online" if result.returncode == 0 else "stopped"
            pid = int(result.stdout.strip()) if result.returncode == 0 else None

            services.append(
                ServiceStatus(
                    service=service_name,
                    status=status,
                    pid=pid,
                    uptime_seconds=None,
                    memory_mb=None,
                )
            )

    return services


@router.get("/system")
async def system_info():
    """
    Get system information.

    Returns:
        Dict with system specs, disk usage, etc.
    """
    import platform
    import shutil

    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "hostname": platform.node(),
    }

    # Disk usage
    try:
        usage = shutil.disk_usage("/")
        info["disk"] = {
            "total_gb": round(usage.total / 1024**3, 2),
            "used_gb": round(usage.used / 1024**3, 2),
            "free_gb": round(usage.free / 1024**3, 2),
            "percent_used": round((usage.used / usage.total) * 100, 2),
        }
    except Exception as e:
        info["disk"] = {"error": str(e)}

    # Memory (if psutil available)
    try:
        import psutil

        mem = psutil.virtual_memory()
        info["memory"] = {
            "total_gb": round(mem.total / 1024**3, 2),
            "available_gb": round(mem.available / 1024**3, 2),
            "percent_used": mem.percent,
        }
    except ImportError:
        info["memory"] = {"error": "psutil not installed"}
    except Exception as e:
        info["memory"] = {"error": str(e)}

    return info


@router.get("/readiness")
async def readiness_check():
    """
    Readiness probe for Kubernetes/PM2.

    Returns:
        200 if service is ready, 503 if not
    """
    # Check if critical paths exist
    corpus_path = Path("storage/corpus.h5")

    if not corpus_path.parent.exists():
        return {"ready": False, "reason": "Storage directory not found"}

    return {"ready": True, "timestamp": datetime.now(UTC).isoformat() + "Z"}


@router.get("/liveness")
async def liveness_check():
    """
    Liveness probe for Kubernetes/PM2.

    Always returns 200 if process is running.
    """
    return {
        "alive": True,
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "pid": os.getpid(),
    }
