"""
Free Intelligence - Retry Logic with Exponential Backoff and Circuit Breaker

Provides resilient API call patterns:
- Exponential backoff with jitter for transient failures
- Circuit breaker to prevent cascade failures
- Configurable thresholds and windows

Card: FI-BACKEND-REF-005
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before half-open
    success_threshold: int = 2  # Successes needed to close from half-open


@dataclass
class RetryConfig:
    """Configuration for exponential backoff retry"""

    max_retries: int = 3
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 30.0  # Maximum delay cap
    exponential_base: float = 2.0  # Multiplier for each retry
    jitter: bool = True  # Add random jitter to prevent thundering herd


@dataclass
class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service failing, reject all calls immediately
    - HALF_OPEN: Testing recovery, allow limited calls

    Example:
        >>> cb = CircuitBreaker(name="ollama")
        >>> if cb.can_execute():
        ...     try:
        ...         result = call_api()
        ...         cb.record_success()
        ...     except Exception as e:
        ...         cb.record_failure()
        ...         raise
    """

    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    # State tracking
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: float | None = field(default=None)

    def can_execute(self) -> bool:
        """Check if a call should be allowed through the circuit breaker."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time is not None:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    logger.info(
                        "CIRCUIT_BREAKER_HALF_OPEN",
                        name=self.name,
                        elapsed_seconds=round(elapsed, 2),
                    )
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    return True
            return False

        # HALF_OPEN: Allow limited calls for testing
        return True

    def record_success(self) -> None:
        """Record a successful call."""
        state_changed = False
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(
                    "CIRCUIT_BREAKER_CLOSED",
                    name=self.name,
                    success_count=self.success_count,
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                state_changed = True
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

        # Persist state on significant changes (lazy import to avoid circular)
        if state_changed:
            try:
                save_circuit_breaker_states()
            except NameError:
                pass  # Function not yet defined during class definition

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        state_changed = False

        if self.state == CircuitState.HALF_OPEN:
            # Immediate trip back to OPEN on failure during half-open
            logger.warning(
                "CIRCUIT_BREAKER_REOPENED",
                name=self.name,
                message="Failed during half-open state",
            )
            self.state = CircuitState.OPEN
            state_changed = True

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.warning(
                    "CIRCUIT_BREAKER_OPENED",
                    name=self.name,
                    failure_count=self.failure_count,
                    threshold=self.config.failure_threshold,
                )
                self.state = CircuitState.OPEN
                state_changed = True

        # Persist state on significant changes (lazy import to avoid circular)
        if state_changed:
            try:
                save_circuit_breaker_states()
            except NameError:
                pass  # Function not yet defined during class definition

    def get_state_info(self) -> dict[str, Any]:
        """Get current circuit breaker state information."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
            },
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    def __init__(self, name: str, message: str = "Circuit breaker is open"):
        self.name = name
        super().__init__(f"{name}: {message}")


def calculate_backoff_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay for exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds

    Example:
        >>> config = RetryConfig(base_delay=1.0, exponential_base=2.0)
        >>> calculate_backoff_delay(0, config)  # ~1.0s
        >>> calculate_backoff_delay(1, config)  # ~2.0s
        >>> calculate_backoff_delay(2, config)  # ~4.0s
    """
    # Exponential delay: base * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base**attempt)

    # Cap at max delay
    delay = min(delay, config.max_delay)

    # Add jitter (±25%) to prevent thundering herd
    if config.jitter:
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0.1, delay)  # Minimum 100ms


def with_retry(
    retry_config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for adding retry logic with exponential backoff and circuit breaker.

    Args:
        retry_config: Configuration for retry behavior
        circuit_breaker: Circuit breaker instance for fault tolerance
        retryable_exceptions: Exceptions that should trigger retry

    Returns:
        Decorated function with retry logic

    Example:
        >>> cb = CircuitBreaker(name="api")
        >>> @with_retry(
        ...     retry_config=RetryConfig(max_retries=3),
        ...     circuit_breaker=cb,
        ... )
        ... def call_api():
        ...     return requests.get("https://api.example.com")
    """
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Check circuit breaker first
            if circuit_breaker and not circuit_breaker.can_execute():
                raise CircuitOpenError(
                    circuit_breaker.name,
                    f"Service unavailable, retry after {circuit_breaker.config.recovery_timeout}s",
                )

            last_exception: Exception | None = None

            for attempt in range(retry_config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Success: record and return
                    if circuit_breaker:
                        circuit_breaker.record_success()

                    if attempt > 0:
                        logger.info(
                            "RETRY_SUCCEEDED",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=retry_config.max_retries + 1,
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # Record failure for circuit breaker
                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    # Check if we have retries left
                    if attempt < retry_config.max_retries:
                        delay = calculate_backoff_delay(attempt, retry_config)

                        logger.warning(
                            "RETRY_ATTEMPT",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=retry_config.max_retries,
                            delay_seconds=round(delay, 2),
                            error=str(e)[:100],
                        )

                        time.sleep(delay)

                        # Re-check circuit breaker after delay
                        if circuit_breaker and not circuit_breaker.can_execute():
                            raise CircuitOpenError(
                                circuit_breaker.name,
                                "Circuit opened during retry sequence",
                            )
                    else:
                        logger.error(
                            "RETRY_EXHAUSTED",
                            function=func.__name__,
                            total_attempts=retry_config.max_retries + 1,
                            error=str(e)[:100],
                        )

            # All retries exhausted
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


async def with_retry_async(
    func: Callable[P, T],
    *args: P.args,
    retry_config: RetryConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: P.kwargs,
) -> T:
    """
    Async version of retry logic with exponential backoff and circuit breaker.

    Args:
        func: Async function to call
        *args: Positional arguments for func
        retry_config: Configuration for retry behavior
        circuit_breaker: Circuit breaker instance for fault tolerance
        retryable_exceptions: Exceptions that should trigger retry
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Example:
        >>> result = await with_retry_async(
        ...     fetch_data,
        ...     url="https://api.example.com",
        ...     retry_config=RetryConfig(max_retries=3),
        ... )
    """
    if retry_config is None:
        retry_config = RetryConfig()

    # Check circuit breaker first
    if circuit_breaker and not circuit_breaker.can_execute():
        raise CircuitOpenError(
            circuit_breaker.name,
            f"Service unavailable, retry after {circuit_breaker.config.recovery_timeout}s",
        )

    last_exception: Exception | None = None

    for attempt in range(retry_config.max_retries + 1):
        try:
            result = await func(*args, **kwargs)

            # Success: record and return
            if circuit_breaker:
                circuit_breaker.record_success()

            if attempt > 0:
                logger.info(
                    "ASYNC_RETRY_SUCCEEDED",
                    function=func.__name__,
                    attempt=attempt + 1,
                    total_attempts=retry_config.max_retries + 1,
                )

            return result

        except retryable_exceptions as e:
            last_exception = e

            # Record failure for circuit breaker
            if circuit_breaker:
                circuit_breaker.record_failure()

            # Check if we have retries left
            if attempt < retry_config.max_retries:
                delay = calculate_backoff_delay(attempt, retry_config)

                logger.warning(
                    "ASYNC_RETRY_ATTEMPT",
                    function=func.__name__,
                    attempt=attempt + 1,
                    max_retries=retry_config.max_retries,
                    delay_seconds=round(delay, 2),
                    error=str(e)[:100],
                )

                await asyncio.sleep(delay)

                # Re-check circuit breaker after delay
                if circuit_breaker and not circuit_breaker.can_execute():
                    raise CircuitOpenError(
                        circuit_breaker.name,
                        "Circuit opened during retry sequence",
                    )
            else:
                logger.error(
                    "ASYNC_RETRY_EXHAUSTED",
                    function=func.__name__,
                    total_attempts=retry_config.max_retries + 1,
                    error=str(e)[:100],
                )

    # All retries exhausted
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected async retry loop exit")


# Global circuit breaker registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: CircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    Args:
        name: Unique identifier for the circuit breaker
        config: Configuration (only used on first creation)

    Returns:
        CircuitBreaker instance

    Example:
        >>> cb = get_circuit_breaker("ollama", CircuitBreakerConfig(failure_threshold=5))
        >>> # Subsequent calls return the same instance
        >>> cb2 = get_circuit_breaker("ollama")
        >>> assert cb is cb2
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            config=config or CircuitBreakerConfig(),
        )
        logger.info(
            "CIRCUIT_BREAKER_CREATED",
            name=name,
            config=_circuit_breakers[name].config.__dict__,
        )

    return _circuit_breakers[name]


def reset_circuit_breaker(name: str) -> None:
    """Reset a circuit breaker to closed state."""
    if name in _circuit_breakers:
        cb = _circuit_breakers[name]
        cb.state = CircuitState.CLOSED
        cb.failure_count = 0
        cb.success_count = 0
        cb.last_failure_time = None
        logger.info("CIRCUIT_BREAKER_RESET", name=name)


def get_all_circuit_breaker_states() -> dict[str, dict[str, Any]]:
    """Get state information for all circuit breakers."""
    return {name: cb.get_state_info() for name, cb in _circuit_breakers.items()}


def get_ollama_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all Ollama-related circuit breakers."""
    return {
        name: cb for name, cb in _circuit_breakers.items()
        if name.startswith("ollama_")
    }


def reset_all_ollama_circuit_breakers() -> None:
    """
    Reset all Ollama circuit breakers to closed state.

    Useful after:
    - Tunnel restart (new URL available)
    - Manual intervention
    - Host recovery
    """
    reset_count = 0
    for name in list(_circuit_breakers.keys()):
        if name.startswith("ollama_"):
            reset_circuit_breaker(name)
            reset_count += 1

    if reset_count > 0:
        logger.info(
            "OLLAMA_CIRCUIT_BREAKERS_RESET_BULK",
            count=reset_count,
        )
        save_circuit_breaker_states()


# Circuit breaker persistence (FI-BACKEND-FALLBACK-001)
_PERSISTENCE_FILE = "/tmp/fi_circuit_breakers.json"


def save_circuit_breaker_states() -> bool:
    """
    Save circuit breaker states to disk for persistence across restarts.

    Returns:
        True if saved successfully, False otherwise
    """
    import json
    from pathlib import Path

    try:
        states = {}
        for name, cb in _circuit_breakers.items():
            states[name] = {
                "state": cb.state.value,
                "failure_count": cb.failure_count,
                "success_count": cb.success_count,
                "last_failure_time": cb.last_failure_time,
            }

        Path(_PERSISTENCE_FILE).write_text(json.dumps(states, indent=2))
        logger.info(
            "CIRCUIT_BREAKER_STATES_SAVED",
            file=_PERSISTENCE_FILE,
            count=len(states),
        )
        return True
    except Exception as e:
        logger.warning(
            "CIRCUIT_BREAKER_STATES_SAVE_FAILED",
            error=str(e)[:100],
        )
        return False


def restore_circuit_breaker_states() -> int:
    """
    Restore circuit breaker states from disk after restart.

    Only restores state for circuit breakers that already exist in the registry.
    Does NOT create new circuit breakers (they must be created via get_circuit_breaker first).

    Returns:
        Number of circuit breakers restored
    """
    import json
    from pathlib import Path

    persistence_file = Path(_PERSISTENCE_FILE)
    if not persistence_file.exists():
        return 0

    try:
        states = json.loads(persistence_file.read_text())
        restored_count = 0

        for name, state_data in states.items():
            if name in _circuit_breakers:
                cb = _circuit_breakers[name]
                cb.state = CircuitState(state_data["state"])
                cb.failure_count = state_data["failure_count"]
                cb.success_count = state_data["success_count"]
                cb.last_failure_time = state_data["last_failure_time"]
                restored_count += 1

        if restored_count > 0:
            logger.info(
                "CIRCUIT_BREAKER_STATES_RESTORED",
                file=_PERSISTENCE_FILE,
                count=restored_count,
            )
        return restored_count
    except Exception as e:
        logger.warning(
            "CIRCUIT_BREAKER_STATES_RESTORE_FAILED",
            error=str(e)[:100],
        )
        return 0
