"""
Free Intelligence - Resilience Executor for Multi-Host LLM Providers

Encapsulates the multi-host fallback pattern with:
- Circuit breaker gating per host
- Exponential backoff retry
- Thread-safe host preference updates

Card: FI-BACKEND-FALLBACK-001
Card: FI-BACKEND-REF-005
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, TypeVar

from backend.providers.retry import CircuitBreaker, CircuitOpenError, RetryConfig, calculate_backoff_delay
from backend.providers.utils import sanitize_error_message
from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.utils.common.config.deployment import OllamaHost

logger = get_logger(__name__)

T = TypeVar("T")


class ResilienceExecutor:
    """
    Executes operations with multi-host resilience patterns.

    Encapsulates:
    - Multi-host fallback loop
    - Exponential backoff retry per host
    - Circuit breaker gating per host
    - Thread-safe host preference updates

    Usage:
        >>> executor = ResilienceExecutor(
        ...     hosts=hosts,
        ...     retry_config=RetryConfig(max_retries=3),
        ...     circuit_breakers=circuit_breakers,
        ...     host_lock=threading.Lock(),
        ... )
        >>>
        >>> def api_call(client, host_url):
        ...     return client.generate(model="qwen3:1.7b", prompt="Hello")
        >>>
        >>> result, host_url = executor.execute(api_call, clients, "generate")
    """

    def __init__(
        self,
        hosts: list["OllamaHost"],
        retry_config: RetryConfig,
        circuit_breakers: dict[str, CircuitBreaker],
        host_lock: threading.Lock,
    ) -> None:
        """
        Initialize ResilienceExecutor.

        Args:
            hosts: List of host configurations with url, name, priority
            retry_config: Configuration for exponential backoff retry
            circuit_breakers: Dict mapping host_url -> CircuitBreaker
            host_lock: Threading lock for safe host preference updates
        """
        self.hosts = hosts
        self.retry_config = retry_config
        self.circuit_breakers = circuit_breakers
        self._host_lock = host_lock
        self.current_host_url: str = str(hosts[0]["url"]) if hosts else ""

    def execute(
        self,
        operation: Callable[[Any, str], T],
        clients: dict[str, Any],
        operation_name: str,
    ) -> tuple[T, str, list[str]]:
        """
        Execute an operation with multi-host fallback and retry.

        Args:
            operation: Callable that takes (client, host_url) and returns result
            clients: Dict mapping host_url -> client instance
            operation_name: Name of operation for logging (e.g., "generate", "embed")

        Returns:
            Tuple of (result, successful_host_url, hosts_tried)

        Raises:
            CircuitOpenError: If all hosts are unavailable
            Exception: Last exception from failed attempts
        """
        last_exception: Exception | None = None
        hosts_tried: list[str] = []

        for host in self.hosts:
            host_url = str(host["url"])
            host_name = str(host["name"])
            client = clients.get(host_url)
            cb = self.circuit_breakers.get(host_url)

            if not client or not cb:
                logger.warning(
                    "RESILIENCE_HOST_MISSING_CLIENT",
                    host=host_name,
                    operation=operation_name,
                )
                continue

            # Skip hosts with open circuit breakers
            if not cb.can_execute():
                logger.info(
                    "RESILIENCE_HOST_SKIPPED_CIRCUIT_OPEN",
                    host=host_name,
                    host_url=host_url,
                    operation=operation_name,
                    recovery_timeout=cb.config.recovery_timeout,
                )
                continue

            hosts_tried.append(host_name)
            logger.info(
                "RESILIENCE_TRYING_HOST",
                host=host_name,
                host_url=host_url,
                operation=operation_name,
                priority=host["priority"],
            )

            # Retry loop for this host
            for attempt in range(self.retry_config.max_retries + 1):
                try:
                    result = operation(client, host_url)

                    # Success: record and update current host (thread-safe)
                    cb.record_success()
                    with self._host_lock:
                        previous_host = self.current_host_url
                        self.current_host_url = host_url
                        if previous_host != host_url:
                            logger.info(
                                "RESILIENCE_HOST_PREFERENCE_CHANGED",
                                previous_host=previous_host,
                                new_host=host_url,
                                new_host_name=host_name,
                                operation=operation_name,
                            )

                    logger.info(
                        "RESILIENCE_OPERATION_SUCCESS",
                        host=host_name,
                        operation=operation_name,
                        retry_attempts=attempt,
                        hosts_tried=hosts_tried,
                    )

                    return result, host_url, hosts_tried

                except Exception as e:
                    last_exception = e
                    sanitized_error = sanitize_error_message(str(e))
                    cb.record_failure()

                    if attempt < self.retry_config.max_retries:
                        delay = calculate_backoff_delay(attempt, self.retry_config)
                        logger.warning(
                            "RESILIENCE_RETRY_ATTEMPT",
                            host=host_name,
                            operation=operation_name,
                            attempt=attempt + 1,
                            max_retries=self.retry_config.max_retries,
                            delay_seconds=round(delay, 2),
                            error=sanitized_error[:100],
                        )
                        time.sleep(delay)

                        # Check if circuit breaker opened during retry
                        if not cb.can_execute():
                            logger.warning(
                                "RESILIENCE_CIRCUIT_OPENED_DURING_RETRY",
                                host=host_name,
                                operation=operation_name,
                            )
                            break  # Move to next host
                    else:
                        logger.warning(
                            "RESILIENCE_HOST_EXHAUSTED",
                            host=host_name,
                            host_url=host_url,
                            operation=operation_name,
                            error=sanitized_error[:100],
                            total_attempts=self.retry_config.max_retries + 1,
                        )
                        break  # Move to next host

        # All hosts exhausted
        logger.error(
            "RESILIENCE_ALL_HOSTS_FAILED",
            operation=operation_name,
            hosts_tried=hosts_tried,
            total_hosts=len(self.hosts),
            last_error=sanitize_error_message(str(last_exception), max_length=200)
            if last_exception
            else "unknown",
        )

        if last_exception:
            raise last_exception
        raise CircuitOpenError("all_hosts", f"All hosts unavailable for {operation_name}")

    def execute_generator(
        self,
        operation: Callable[[Any, str], Generator[T, None, None]],
        clients: dict[str, Any],
        operation_name: str,
    ) -> Generator[tuple[T, str, list[str]] | T, None, None]:
        """
        Execute a streaming operation with multi-host fallback and retry.

        Yields chunks from the generator operation. On success, updates host preference.
        On failure, falls back to next host.

        Args:
            operation: Callable that takes (client, host_url) and returns a generator
            clients: Dict mapping host_url -> client instance
            operation_name: Name of operation for logging

        Yields:
            Chunks from the successful operation

        Raises:
            CircuitOpenError: If all hosts are unavailable
            Exception: Last exception from failed attempts

        Note:
            For streaming, we can't easily retry mid-stream, so we:
            1. Attempt to start the stream
            2. If stream starts successfully, yield all chunks
            3. If stream fails to start, retry or move to next host
        """
        last_exception: Exception | None = None
        hosts_tried: list[str] = []

        for host in self.hosts:
            host_url = str(host["url"])
            host_name = str(host["name"])
            client = clients.get(host_url)
            cb = self.circuit_breakers.get(host_url)

            if not client or not cb:
                continue

            if not cb.can_execute():
                logger.info(
                    "RESILIENCE_STREAM_HOST_SKIPPED_CIRCUIT_OPEN",
                    host=host_name,
                    operation=operation_name,
                )
                continue

            hosts_tried.append(host_name)
            logger.info(
                "RESILIENCE_STREAM_TRYING_HOST",
                host=host_name,
                operation=operation_name,
                priority=host["priority"],
            )

            for attempt in range(self.retry_config.max_retries + 1):
                try:
                    # Get the generator
                    gen = operation(client, host_url)

                    # Start yielding - if this works, the stream started successfully
                    chunk_count = 0
                    for chunk in gen:
                        chunk_count += 1
                        yield chunk

                    # Stream completed successfully
                    cb.record_success()
                    with self._host_lock:
                        previous_host = self.current_host_url
                        self.current_host_url = host_url
                        if previous_host != host_url:
                            logger.info(
                                "RESILIENCE_HOST_PREFERENCE_CHANGED",
                                previous_host=previous_host,
                                new_host=host_url,
                                new_host_name=host_name,
                                operation=operation_name,
                            )

                    logger.info(
                        "RESILIENCE_STREAM_COMPLETED",
                        host=host_name,
                        operation=operation_name,
                        chunks_yielded=chunk_count,
                        hosts_tried=hosts_tried,
                    )
                    return  # Success - exit generator

                except Exception as e:
                    last_exception = e
                    sanitized_error = sanitize_error_message(str(e))
                    cb.record_failure()

                    if attempt < self.retry_config.max_retries:
                        delay = calculate_backoff_delay(attempt, self.retry_config)
                        logger.warning(
                            "RESILIENCE_STREAM_RETRY_ATTEMPT",
                            host=host_name,
                            operation=operation_name,
                            attempt=attempt + 1,
                            delay_seconds=round(delay, 2),
                            error=sanitized_error[:100],
                        )
                        time.sleep(delay)
                        if not cb.can_execute():
                            break
                    else:
                        logger.warning(
                            "RESILIENCE_STREAM_HOST_EXHAUSTED",
                            host=host_name,
                            operation=operation_name,
                            error=sanitized_error[:100],
                        )
                        break

        # All hosts exhausted
        logger.error(
            "RESILIENCE_STREAM_ALL_HOSTS_FAILED",
            operation=operation_name,
            hosts_tried=hosts_tried,
            last_error=sanitize_error_message(str(last_exception), max_length=200)
            if last_exception
            else "unknown",
        )

        if last_exception:
            raise last_exception
        raise CircuitOpenError("all_hosts", f"All hosts unavailable for streaming {operation_name}")
