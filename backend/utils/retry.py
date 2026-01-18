"""Retry logic with exponential backoff - Resilience for external API calls.

Philosophy:
  - External APIs fail transiently (network, rate limits, timeouts)
  - Exponential backoff prevents thundering herd
  - Circuit breaker prevents cascading failures
  - Observability: log every retry attempt

Architecture:
  - @retry_with_backoff decorator for functions
  - Configurable max attempts, base delay, max delay
  - Jitter to avoid synchronized retries
  - Exception filtering (only retry transient errors)

Created: 2025-12-03
Pattern: Exponential Backoff + Jitter
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from collections.abc import Callable
from typing import Any, Type

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRANSIENT EXCEPTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Exceptions that should trigger retry (transient errors)
DEFAULT_RETRYABLE_EXCEPTIONS = (
    # Network errors
    ConnectionError,
    TimeoutError,
    # HTTP errors (429 Rate Limit, 503 Service Unavailable, 504 Gateway Timeout)
    # These are handled by provider-specific retry logic
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RETRY DECORATOR (SYNC)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add random jitter to delay (default: True)
        exceptions: Tuple of exception types to retry (default: network errors)

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_attempts=5, base_delay=2.0)
        def call_external_api():
            response = requests.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()

    Behavior:
        - Attempt 1: No delay
        - Attempt 2: base_delay * exponential_base^1 + jitter
        - Attempt 3: base_delay * exponential_base^2 + jitter
        - ...
        - Max delay capped at max_delay
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # Execute function
                    result = func(*args, **kwargs)

                    # Success - log if retry was needed
                    if attempt > 1:
                        logger.info(
                            "RETRY_SUCCESS",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Last attempt - raise exception
                    if attempt == max_attempts:
                        logger.error(
                            "RETRY_EXHAUSTED",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                            exc_info=True,
                        )
                        raise

                    # Calculate delay: base_delay * exponential_base^(attempt-1)
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter (random 0-25% of delay)
                    if jitter:
                        delay += random.uniform(0, delay * 0.25)

                    logger.warning(
                        "RETRY_ATTEMPT",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=round(delay, 2),
                        error=str(e),
                    )

                    # Wait before retry
                    time.sleep(delay)

            # Should never reach here, but handle edge case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ASYNC RETRY DECORATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
) -> Callable:
    """
    Async decorator for retrying async functions with exponential backoff.

    Same as retry_with_backoff but for async functions.

    Example:
        @async_retry_with_backoff(max_attempts=5, base_delay=2.0)
        async def call_external_api():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/data")
                response.raise_for_status()
                return response.json()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # Execute async function
                    result = await func(*args, **kwargs)

                    # Success - log if retry was needed
                    if attempt > 1:
                        logger.info(
                            "ASYNC_RETRY_SUCCESS",
                            function=func.__name__,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Last attempt - raise exception
                    if attempt == max_attempts:
                        logger.error(
                            "ASYNC_RETRY_EXHAUSTED",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                            exc_info=True,
                        )
                        raise

                    # Calculate delay
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter
                    if jitter:
                        delay += random.uniform(0, delay * 0.25)

                    logger.warning(
                        "ASYNC_RETRY_ATTEMPT",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=round(delay, 2),
                        error=str(e),
                    )

                    # Wait before retry
                    await asyncio.sleep(delay)

            # Should never reach here, but handle edge case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
