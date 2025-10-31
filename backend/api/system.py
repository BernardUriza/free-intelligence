"""
System Health API - Unified health checks for all services

Card: FI-UI-FEAT-206 (Diarization Progress + Health + Path Hardening)
File: backend/api/system.py
Created: 2025-10-30

Endpoints:
  GET /api/system/health - Unified health check aggregating all services
"""

import os
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Optional, Any, List

from fastapi import APIRouter
from pydantic import BaseModel

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system")


class SystemHealthResponse(BaseModel):
    """Unified system health response"""
    ok: bool
    services: Dict[str, Any]
    version: str
    time: str


def check_backend_health() -> bool:
    """Backend is always healthy if we can respond."""
    return True


def check_diarization_health() -> Dict[str, bool]:
    """
    Check diarization service health.

    Checks:
    - Whisper: faster-whisper import + model can load (non-allocating)
    - ffmpeg: ffprobe -version (non-blocking)

    Returns:
        Dict with whisper and ffmpeg booleans
    """
    # Check Whisper
    whisper_ok = False
    try:
        from backend.whisper_service import is_whisper_available
        whisper_ok = is_whisper_available()
    except Exception as e:
        logger.warning("WHISPER_CHECK_FAILED", error=str(e))

    # Check ffmpeg/ffprobe
    ffmpeg_ok = False
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=2,
            text=True
        )
        ffmpeg_ok = result.returncode == 0
    except Exception as e:
        logger.warning("FFMPEG_CHECK_FAILED", error=str(e))

    return {
        "whisper": whisper_ok,
        "ffmpeg": ffmpeg_ok
    }


def check_llm_health() -> Dict[str, Any]:
    """
    Check LLM service health.

    Checks:
    - Ollama: GET http://127.0.0.1:11434/api/tags (timeout 800ms)

    Returns:
        Dict with ollama boolean and models list
    """
    ollama_ok = False
    models = []

    try:
        import requests
        from backend.diarization_service import OLLAMA_BASE_URL

        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=0.8
        )

        if response.status_code == 200:
            ollama_ok = True
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
    except Exception as e:
        logger.debug("OLLAMA_CHECK_FAILED", error=str(e))

    return {
        "ollama": ollama_ok,
        "models": models
    }


def check_policy_health() -> bool:
    """
    Check policy service health.

    Attempts to instantiate PolicyEnforcer without raising.

    Returns:
        True if PolicyEnforcer can be instantiated
    """
    try:
        from backend.policy_enforcer import PolicyEnforcer
        enforcer = PolicyEnforcer()
        return True
    except Exception as e:
        logger.warning("POLICY_CHECK_FAILED", error=str(e))
        return False


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health() -> SystemHealthResponse:
    """
    Unified health check aggregating all services.

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
    backend_ok = check_backend_health()
    diarization = check_diarization_health()
    llm = check_llm_health()
    policy_ok = check_policy_health()

    # Critical services: backend, diarization.whisper, diarization.ffmpeg, policy
    # LLM is optional (graceful degradation)
    critical_ok = (
        backend_ok and
        diarization.get("whisper", False) and
        diarization.get("ffmpeg", False) and
        policy_ok
    )

    services = {
        "backend": backend_ok,
        "diarization": diarization,
        "llm": llm,
        "policy": policy_ok
    }

    return SystemHealthResponse(
        ok=critical_ok,
        services=services,
        version="v0.3.0",
        time=datetime.utcnow().isoformat() + "Z"
    )
