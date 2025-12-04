"""Circuit Breaker pattern - Prevents cascading failures from external services.

Philosophy:
  - External services fail (Azure, Deepgram, Claude, OpenAI)
  - Cascading failures destroy system reliability
  - Circuit breaker fails fast when service is down
  - Automatic recovery detection

Architecture:
  - CLOSED: Normal operation, requests pass through
  - OPEN: Fail fast, don't call service (circuit breaker tripped)
  - HALF_OPEN: Testing recovery, limited requests
  - Automatic state transitions based on failure/success rates

Created: 2025-12-03
Pattern: Circuit Breaker (Nygard "Release It!")
"""

from __future__ import annotations

import functools
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Type

from backend.logger import get_logger

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CIRCUIT BREAKER STATES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing fast, circuit tripped
    HALF_OPEN = "half_open"  # Testing recovery


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXCEPTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is OPEN (service unavailable)"""

    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker OPEN for {service_name}. "
            f"Service unavailable, retry after {retry_after:.1f}s"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CALL RESULT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class CallResult:
    """Result of a call through circuit breaker"""

    timestamp: float
    success: bool
    duration_ms: float
    exception_type: str | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CIRCUIT BREAKER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Monitors failure rate and fails fast when service is unhealthy.

    Configuration:
        - failure_threshold: Failures before opening (default: 5)
        - recovery_timeout: Seconds before trying half-open (default: 60)
        - success_threshold: Successes in half-open before closing (default: 2)
        - window_size: Time window for failure counting in seconds (default: 60)
        - excluded_exceptions: Exceptions that don't count as failures

    State transitions:
        CLOSED -> OPEN: After failure_threshold failures in window
        OPEN -> HALF_OPEN: After recovery_timeout seconds
        HALF_OPEN -> CLOSED: After success_threshold successes
        HALF_OPEN -> OPEN: After any failure

    Usage as decorator:
        @circuit_breaker(name="deepgram")
        def call_deepgram_api():
            return requests.post(...)

    Usage as context manager:
        with circuit_breaker_context("deepgram") as breaker:
            result = call_deepgram_api()
            return result
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
        window_size: float = 60.0,
        excluded_exceptions: tuple[Type[Exception], ...] = (),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.window_size = window_size
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._opened_at: float | None = None

        # Sliding window of recent calls
        self._call_history: deque[CallResult] = deque(maxlen=100)

        self._lock = threading.RLock()
        self.logger = get_logger(__name__)

        self.logger.info(
            "CIRCUIT_BREAKER_INITIALIZED",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state (thread-safe)"""
        with self._lock:
            return self._state

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate in current window"""
        with self._lock:
            now = time.time()
            recent_calls = [
                call for call in self._call_history if (now - call.timestamp) < self.window_size
            ]

            if not recent_calls:
                return 0.0

            failures = sum(1 for call in recent_calls if not call.success)
            return failures / len(recent_calls)

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should transition from OPEN to HALF_OPEN"""
        with self._lock:
            if self._state != CircuitState.OPEN:
                return False

            if self._opened_at is None:
                return False

            # Check if recovery timeout elapsed
            elapsed = time.time() - self._opened_at
            return elapsed >= self.recovery_timeout

    def _record_success(self, duration_ms: float) -> None:
        """Record successful call"""
        with self._lock:
            now = time.time()

            # Add to history
            self._call_history.append(
                CallResult(timestamp=now, success=True, duration_ms=duration_ms)
            )

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1

                self.logger.info(
                    "CIRCUIT_BREAKER_HALF_OPEN_SUCCESS",
                    name=self.name,
                    success_count=self._success_count,
                    success_threshold=self.success_threshold,
                )

                # Enough successes to close circuit
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    self._opened_at = None

                    self.logger.info(
                        "CIRCUIT_BREAKER_CLOSED",
                        name=self.name,
                        reason="recovery_confirmed",
                    )

    def _record_failure(self, exception: Exception, duration_ms: float) -> None:
        """Record failed call"""
        with self._lock:
            now = time.time()

            # Check if exception should be ignored
            if isinstance(exception, self.excluded_exceptions):
                self.logger.debug(
                    "CIRCUIT_BREAKER_EXCLUDED_EXCEPTION",
                    name=self.name,
                    exception_type=type(exception).__name__,
                )
                return

            # Add to history
            self._call_history.append(
                CallResult(
                    timestamp=now,
                    success=False,
                    duration_ms=duration_ms,
                    exception_type=type(exception).__name__,
                )
            )

            self._last_failure_time = now

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._state = CircuitState.OPEN
                self._opened_at = now
                self._success_count = 0

                self.logger.warning(
                    "CIRCUIT_BREAKER_REOPENED",
                    name=self.name,
                    reason="half_open_failure",
                    exception_type=type(exception).__name__,
                )

            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1

                # Check if we should open circuit
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = now

                    self.logger.error(
                        "CIRCUIT_BREAKER_OPENED",
                        name=self.name,
                        failure_count=self._failure_count,
                        failure_threshold=self.failure_threshold,
                        recovery_timeout=self.recovery_timeout,
                    )

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from function
        """
        with self._lock:
            # Check if we should attempt reset
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0

                self.logger.info(
                    "CIRCUIT_BREAKER_HALF_OPEN",
                    name=self.name,
                    reason="recovery_timeout_elapsed",
                )

            # Fail fast if circuit is open
            if self._state == CircuitState.OPEN:
                retry_after = self.recovery_timeout - (time.time() - (self._opened_at or 0))
                retry_after = max(0, retry_after)

                self.logger.warning(
                    "CIRCUIT_BREAKER_REJECTING_CALL",
                    name=self.name,
                    state=self._state.value,
                    retry_after=round(retry_after, 1),
                )

                raise CircuitBreakerOpen(self.name, retry_after)

        # Execute function
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            self._record_success(duration_ms)
            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._record_failure(e, duration_ms)
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics"""
        with self._lock:
            now = time.time()
            recent_calls = [
                call for call in self._call_history if (now - call.timestamp) < self.window_size
            ]

            return {
                "name": self.name,
                "state": self._state.value,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "current_failures": self._failure_count,
                "current_successes": self._success_count,
                "failure_rate": self.failure_rate,
                "recent_calls_count": len(recent_calls),
                "opened_at": (
                    datetime.fromtimestamp(self._opened_at).isoformat() if self._opened_at else None
                ),
                "time_until_recovery": (
                    max(0, self.recovery_timeout - (now - (self._opened_at or 0)))
                    if self._opened_at
                    else None
                ),
            }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL CIRCUIT BREAKER REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 2,
    window_size: float = 60.0,
    excluded_exceptions: tuple[Type[Exception], ...] = (),
) -> CircuitBreaker:
    """
    Get or create circuit breaker (singleton per name).

    Args:
        name: Circuit breaker name (e.g., "deepgram", "azure_whisper" deprecated)
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before trying recovery
        success_threshold: Successes before closing
        window_size: Time window for failure counting
        excluded_exceptions: Exceptions that don't count as failures

    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
                window_size=window_size,
                excluded_exceptions=excluded_exceptions,
            )

        return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all registered circuit breakers"""
    with _registry_lock:
        return dict(_circuit_breakers)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DECORATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 2,
    window_size: float = 60.0,
    excluded_exceptions: tuple[Type[Exception], ...] = (),
) -> Callable:
    """
    Decorator for protecting functions with circuit breaker.

    Example:
        @circuit_breaker(name="deepgram", failure_threshold=3)
        def call_deepgram_api():
            return requests.post(...)

    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before trying recovery
        success_threshold: Successes before closing
        window_size: Time window for failure counting
        excluded_exceptions: Exceptions that don't count as failures

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            window_size=window_size,
            excluded_exceptions=excluded_exceptions,
        )

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return breaker.call(func, *args, **kwargs)

        return wrapper

    return decorator
