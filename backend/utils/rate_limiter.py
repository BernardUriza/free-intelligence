"""Rate Limiter (Generic).

Generic rate limiter for API calls. Originally created for Azure Whisper
(3 requests per minute), but Azure Whisper endpoint has been removed.

This module is kept for backward compatibility and potential future use.

Usage:
    from backend.utils.rate_limiter import RateLimiter

    limiter = RateLimiter(max_calls=3, period_seconds=60.0)
    with limiter:
        result = call_api(data)
"""

from __future__ import annotations

import threading
import time

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter (thread-safe)."""

    def __init__(self, max_calls: int, period_seconds: float):
        """Initialize rate limiter.

        Args:
            max_calls: Maximum calls allowed in period
            period_seconds: Time window in seconds
        """
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls: list[float] = []  # Timestamps of recent calls
        self.lock = threading.Lock()

    def wait_if_needed(self) -> float:
        """Wait if rate limit would be exceeded.

        Returns:
            Seconds waited (0 if no wait needed)
        """
        with self.lock:
            now = time.time()

            # Remove old calls outside the window
            cutoff = now - self.period
            self.calls = [t for t in self.calls if t > cutoff]

            # Check if we need to wait
            if len(self.calls) >= self.max_calls:
                oldest = self.calls[0]
                wait_until = oldest + self.period
                wait_seconds = wait_until - now

                if wait_seconds > 0:
                    logger.warning(
                        "RATE_LIMIT_WAIT",
                        calls=len(self.calls),
                        max_calls=self.max_calls,
                        period=self.period,
                        wait_seconds=round(wait_seconds, 2),
                    )
                    time.sleep(wait_seconds)
                    waited = wait_seconds
                else:
                    waited = 0.0
            else:
                waited = 0.0

            # Record this call
            self.calls.append(time.time())
            return waited

    def __enter__(self):
        """Context manager entry."""
        self.wait_if_needed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


# Global rate limiter instance for Azure Whisper (DEPRECATED - endpoint removed)
# Kept for backward compatibility in case AzureWhisperProvider is still referenced
azure_whisper_rate_limiter = RateLimiter(max_calls=3, period_seconds=60.0)
