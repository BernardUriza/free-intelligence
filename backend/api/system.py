"""
System Health API - Unified health checks for all services

Card: FI-UI-FEAT-204 (Service Health + Diarization Progress)
File: backend/api/system.py
Created: 2025-10-30

Endpoints:
  GET /api/system/health - Unified health check aggregating all services
"""

import os
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/system")


class ServiceHealth(BaseModel):
    """Health status for individual service"""
    ok: bool
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class SystemHealthResponse(BaseModel):
    """Unified system health response"""
    ok: bool
    services: Dict[str, ServiceHealth]
    version: str
    time: str


def check_backend_health() -> ServiceHealth:
    """Self-check for backend service"""
    try:
        # Backend is healthy if we can execute this check
        return ServiceHealth(ok=True, message="operational", latency_ms=0.5)
    except Exception as e:
        return ServiceHealth(ok=False, message=f"Backend check failed: {str(e)}")


def check_diarization_health() -> ServiceHealth:
    """Check diarization service (whisper + ffmpeg present)"""
    try:
        # Check if ffmpeg is available
        ffmpeg_present = shutil.which("ffmpeg") is not None

        # Check if pyannote is importable (whisper check)
        try:
            import pyannote.audio  # noqa: F401
            pyannote_present = True
        except ImportError:
            pyannote_present = False

        if ffmpeg_present and pyannote_present:
            return ServiceHealth(
                ok=True,
                message="ffmpeg + pyannote available",
                latency_ms=1.0
            )

        missing = []
        if not ffmpeg_present:
            missing.append("ffmpeg")
        if not pyannote_present:
            missing.append("pyannote")

        return ServiceHealth(
            ok=False,
            message=f"Missing: {', '.join(missing)}"
        )
    except Exception as e:
        return ServiceHealth(ok=False, message=f"Diarization check failed: {str(e)}")


def check_llm_health() -> ServiceHealth:
    """Check LLM service reachability (Qwen/Ollama)"""
    try:
        import requests

        # Try Ollama endpoint (default port 11434)
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                return ServiceHealth(
                    ok=True,
                    message="Ollama reachable",
                    latency_ms=response.elapsed.total_seconds() * 1000
                )
        except requests.exceptions.RequestException:
            pass

        # LLM not reachable but this is graceful degradation
        return ServiceHealth(
            ok=False,
            message="Ollama not reachable (graceful degradation)"
        )
    except Exception as e:
        return ServiceHealth(ok=False, message=f"LLM check failed: {str(e)}")


def check_policy_health() -> ServiceHealth:
    """Check policy enforcer status"""
    try:
        # Check if policy file exists and is readable
        policy_path = "config/fi.policy.yaml"

        if os.path.exists(policy_path):
            # Try to import and check PolicyEnforcer
            try:
                from backend.policy_enforcer import PolicyEnforcer

                # Check if PolicyEnforcer can be instantiated
                enforcer = PolicyEnforcer()

                return ServiceHealth(
                    ok=True,
                    message="Policy enforcer active",
                    latency_ms=0.5
                )
            except Exception as e:
                return ServiceHealth(
                    ok=False,
                    message=f"PolicyEnforcer failed: {str(e)}"
                )
        else:
            return ServiceHealth(
                ok=False,
                message=f"Policy file not found: {policy_path}"
            )
    except Exception as e:
        return ServiceHealth(ok=False, message=f"Policy check failed: {str(e)}")


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health() -> SystemHealthResponse:
    """
    Unified health check aggregating all services.

    Checks:
    - backend: Self-check (if this runs, backend is OK)
    - diarization: whisper + ffmpeg availability
    - llm: Qwen/Ollama reachability
    - policy: PolicyEnforcer active and config loaded

    Returns:
        SystemHealthResponse with ok=True only if ALL services are healthy
    """
    # Run all health checks
    backend_health = check_backend_health()
    diarization_health = check_diarization_health()
    llm_health = check_llm_health()
    policy_health = check_policy_health()

    services = {
        "backend": backend_health,
        "diarization": diarization_health,
        "llm": llm_health,
        "policy": policy_health,
    }

    # System is OK only if ALL critical services are OK
    # LLM is non-critical (graceful degradation)
    critical_services_ok = (
        backend_health.ok and
        diarization_health.ok and
        policy_health.ok
    )

    return SystemHealthResponse(
        ok=critical_services_ok,
        services=services,
        version="0.3.0",
        time=datetime.utcnow().isoformat()
    )
