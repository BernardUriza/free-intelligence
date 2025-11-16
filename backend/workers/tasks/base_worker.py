"""Base worker functionality - DRY principles."""

from __future__ import annotations

import time
from typing import Any

from backend.logger import get_logger

logger = get_logger(__name__)


class WorkerResult:
    """Standardized worker result."""

    def __init__(
        self,
        *,
        session_id: str | None = None,
        status: str = "SUCCESS",
        result: dict[str, Any] | None = None,
        duration_seconds: float = 0.0,
        **kwargs: Any,
    ) -> None:
        self.session_id = session_id
        self.status = status
        self.result = result or {}
        self.duration_seconds = duration_seconds
        self.extra = kwargs

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        data = {
            "status": self.status,
            "result": self.result,
            "duration_seconds": self.duration_seconds,
        }
        if self.session_id:
            data["session_id"] = self.session_id
        data.update(self.extra)
        return data


def measure_time(func):
    """Decorator to measure execution time."""

    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start

            # Inject duration if result is WorkerResult
            if isinstance(result, WorkerResult):
                result.duration_seconds = elapsed
                return result.to_dict()
            elif isinstance(result, dict):
                result["duration_seconds"] = elapsed
            return result
        except Exception:
            raise

    return wrapper
