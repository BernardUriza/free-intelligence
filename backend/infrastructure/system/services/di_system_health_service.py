"""DI System Health Service - Refactored with dependency injection.

Handles system health checks with injected logger for better testability.
"""

from __future__ import annotations

import subprocess
from typing import Any

from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.validation import validate_dependency


class DISystemHealthService:
    """System health service with dependency injection.

    Responsibilities:
    - Check backend service availability
    - Check diarization service (Whisper, FFmpeg)
    - Check LLM service (Ollama)
    - Check policy service (PolicyEnforcer)
    - Aggregate health status
    """

    def __init__(self, logger: ILogger) -> None:
        """Initialize service with injected logger.

        Args:
            logger: Logger instance (required)

        Raises:
            ValueError: If logger is None
            TypeError: If logger doesn't implement ILogger
        """
        validate_dependency(logger, ILogger, "logger")
        self.logger = logger

    def check_backend_health(self) -> bool:
        """Check backend service health.

        Backend is always healthy if we can respond to this request.

        Returns:
            True (always healthy)
        """
        self.logger.info("BACKEND_HEALTH_CHECKED: healthy")
        return True

    def check_diarization_health(self) -> dict[str, Any]:
        """Check diarization service health.

        Checks:
        - Whisper: faster-whisper import + model availability
        - FFmpeg: ffprobe command execution (2s timeout)

        Returns:
            Dict with whisper and ffmpeg availability booleans
        """
        diarization_status = {}

        # Check Whisper availability
        whisper_ok = False
        try:
            from backend.utils.coder.services.whisper_service import is_whisper_available

            whisper_ok = is_whisper_available()
            self.logger.info(f"WHISPER_HEALTH_CHECKED: available={whisper_ok}")
        except Exception as e:
            self.logger.warning(f"WHISPER_CHECK_FAILED: error={e!s}")

        diarization_status["whisper"] = whisper_ok

        # Check FFmpeg availability
        ffmpeg_ok = False
        try:
            result = subprocess.run(
                ["ffprobe", "-version"], capture_output=True, timeout=2, text=True
            )
            ffmpeg_ok = result.returncode == 0
            self.logger.info(f"FFMPEG_HEALTH_CHECKED: available={ffmpeg_ok}")
        except Exception as e:
            self.logger.warning(f"FFMPEG_CHECK_FAILED: error={e!s}")

        diarization_status["ffmpeg"] = ffmpeg_ok

        return diarization_status

    def check_llm_health(self) -> dict[str, Any]:
        """Check LLM service health.

        Checks:
        - Ollama: HTTP GET /api/tags (800ms timeout)
        - Lists available models if Ollama is healthy

        Returns:
            Dict with ollama availability and available models
        """
        ollama_ok = False
        models = []

        try:
            import requests

            OLLAMA_BASE_URL = "http://localhost:11434"

            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=0.8)

            if response.status_code == 200:
                ollama_ok = True
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                self.logger.info(f"OLLAMA_HEALTH_CHECKED: available=True, models={len(models)}")
            else:
                self.logger.warning(f"OLLAMA_CHECK_FAILED: status={response.status_code}")
        except Exception as e:
            self.logger.debug(f"OLLAMA_CHECK_FAILED: error={e!s}")

        return {"ollama": ollama_ok, "models": models}

    def check_policy_health(self) -> bool:
        """Check policy service health.

        Attempts to instantiate PolicyEnforcer without raising exception.
        This validates that policy configuration is available and parseable.

        Returns:
            True if PolicyEnforcer can be instantiated, False otherwise
        """
        try:
            from backend.policy.policy_enforcer import PolicyEnforcer

            _enforcer = PolicyEnforcer()
            self.logger.info("POLICY_HEALTH_CHECKED: healthy")
            return True
        except Exception as e:
            self.logger.warning(f"POLICY_CHECK_FAILED: error={e!s}")
            return False

    def get_system_health(self) -> dict[str, Any]:
        """Get comprehensive system health status.

        Aggregates health checks for all critical services:
        - Backend
        - Diarization (Whisper + FFmpeg)
        - Policy (critical)
        - LLM (optional)

        Returns:
            Dict with overall health status and per-service details
        """
        backend_ok = self.check_backend_health()
        diarization = self.check_diarization_health()
        llm = self.check_llm_health()
        policy_ok = self.check_policy_health()

        critical_ok = (
            backend_ok
            and diarization.get("whisper", False)
            and diarization.get("ffmpeg", False)
            and policy_ok
        )

        services = {
            "backend": backend_ok,
            "diarization": diarization,
            "llm": llm,
            "policy": policy_ok,
        }

        self.logger.info(f"SYSTEM_HEALTH_CHECKED: overall={critical_ok}, services={services}")

        return {
            "ok": critical_ok,
            "services": services,
        }
