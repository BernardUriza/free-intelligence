"""Tests for Retry pattern with exponential backoff.

Coverage target: 100% of backend/utils/retry.py
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from backend.utils.retry import (
    DEFAULT_RETRYABLE_EXCEPTIONS,
    async_retry_with_backoff,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Test sync retry_with_backoff decorator."""

    def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_connection_error(self):
        """Test retries on ConnectionError."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_retry_on_timeout_error(self):
        """Test retries on TimeoutError."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Operation timed out")
            return "recovered"

        result = timeout_func()

        assert result == "recovered"
        assert call_count == 2

    def test_exhausted_retries_raises(self):
        """Test exception is raised after max attempts."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Still failing")

        with pytest.raises(ConnectionError) as exc_info:
            always_fails()

        assert call_count == 3
        assert "Still failing" in str(exc_info.value)

    def test_non_retryable_exception_immediate_raise(self):
        """Test non-retryable exceptions are raised immediately."""
        call_count = 0

        @retry_with_backoff(max_attempts=5, base_delay=0.01)
        def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            value_error_func()

        # Should only be called once
        assert call_count == 1

    def test_custom_exception_types(self):
        """Test custom exception types for retry."""
        call_count = 0

        class CustomTransientError(Exception):
            pass

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            exceptions=(CustomTransientError,),
        )
        def custom_error_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CustomTransientError("Transient")
            return "recovered"

        result = custom_error_func()

        assert result == "recovered"
        assert call_count == 3

    def test_exponential_backoff_delays(self):
        """Test delays follow exponential pattern."""
        delays = []
        call_count = 0

        with patch("time.sleep", side_effect=lambda d: delays.append(d)):
            @retry_with_backoff(
                max_attempts=4,
                base_delay=1.0,
                exponential_base=2.0,
                jitter=False,  # Disable jitter for predictable delays
            )
            def failing_func():
                nonlocal call_count
                call_count += 1
                raise ConnectionError()

            with pytest.raises(ConnectionError):
                failing_func()

        # 3 retries = 3 delays (after attempts 1, 2, 3)
        assert len(delays) == 3
        # Base delay: 1.0, 2.0, 4.0
        assert delays[0] == 1.0  # 1.0 * 2^0
        assert delays[1] == 2.0  # 1.0 * 2^1
        assert delays[2] == 4.0  # 1.0 * 2^2

    def test_max_delay_capped(self):
        """Test delay is capped at max_delay."""
        delays = []

        with patch("time.sleep", side_effect=lambda d: delays.append(d)):
            @retry_with_backoff(
                max_attempts=5,
                base_delay=10.0,
                max_delay=15.0,
                exponential_base=2.0,
                jitter=False,
            )
            def failing_func():
                raise ConnectionError()

            with pytest.raises(ConnectionError):
                failing_func()

        # All delays should be <= max_delay
        assert all(d <= 15.0 for d in delays)

    def test_jitter_adds_randomness(self):
        """Test jitter adds random component to delay."""
        delays_with_jitter = []

        # Run multiple times to observe variance
        for _ in range(3):
            with patch("time.sleep", side_effect=lambda d: delays_with_jitter.append(d)):
                @retry_with_backoff(
                    max_attempts=2,
                    base_delay=1.0,
                    jitter=True,
                )
                def failing_func():
                    raise ConnectionError()

                with pytest.raises(ConnectionError):
                    failing_func()

        # With jitter, delays should vary (base + 0-25% jitter)
        assert len(delays_with_jitter) == 3
        # All delays should be >= base and <= base * 1.25
        assert all(1.0 <= d <= 1.25 for d in delays_with_jitter)

    def test_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""
        @retry_with_backoff()
        def documented_function():
            """Important docstring."""
            return True

        assert documented_function.__name__ == "documented_function"
        assert "Important" in documented_function.__doc__

    def test_passes_args_and_kwargs(self):
        """Test decorator passes arguments correctly."""
        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def func_with_args(a, b, kwarg1=None, kwarg2=None):
            return f"{a}-{b}-{kwarg1}-{kwarg2}"

        result = func_with_args("x", "y", kwarg1="k1", kwarg2="k2")
        assert result == "x-y-k1-k2"


class TestAsyncRetryWithBackoff:
    """Test async retry_with_backoff decorator."""

    @pytest.mark.asyncio
    async def test_successful_async_call(self):
        """Test successful async call doesn't retry."""
        call_count = 0

        @async_retry_with_backoff(max_attempts=3)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "async success"

        result = await async_success()

        assert result == "async success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_on_error(self):
        """Test async retries on transient error."""
        call_count = 0

        @async_retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Async connection refused")
            return "async recovered"

        result = await async_flaky()

        assert result == "async recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_exhausted_raises(self):
        """Test async raises after max attempts."""
        call_count = 0

        @async_retry_with_backoff(max_attempts=2, base_delay=0.01)
        async def async_always_fails():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Always fails async")

        with pytest.raises(TimeoutError):
            await async_always_fails()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_non_retryable_immediate_raise(self):
        """Test non-retryable exceptions raised immediately in async."""
        call_count = 0

        @async_retry_with_backoff(max_attempts=5, base_delay=0.01)
        async def async_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable async")

        with pytest.raises(ValueError):
            await async_value_error()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_uses_asyncio_sleep(self):
        """Test async version uses asyncio.sleep not time.sleep."""
        sleep_calls = []

        with patch("asyncio.sleep", side_effect=lambda d: asyncio.sleep(0)):
            # Also track calls
            original_sleep = asyncio.sleep
            async def tracking_sleep(d):
                sleep_calls.append(d)
                # Don't actually sleep

            with patch("backend.utils.retry.asyncio.sleep", tracking_sleep):
                @async_retry_with_backoff(
                    max_attempts=2,
                    base_delay=1.0,
                    jitter=False,
                )
                async def async_failing():
                    raise ConnectionError()

                with pytest.raises(ConnectionError):
                    await async_failing()

        # Should have recorded sleep calls
        assert len(sleep_calls) == 1

    @pytest.mark.asyncio
    async def test_async_custom_exceptions(self):
        """Test async with custom exception types."""
        call_count = 0

        class AsyncTransientError(Exception):
            pass

        @async_retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            exceptions=(AsyncTransientError,),
        )
        async def async_custom_error():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise AsyncTransientError("Async transient")
            return "async recovered"

        result = await async_custom_error()

        assert result == "async recovered"
        assert call_count == 3


class TestDefaultRetryableExceptions:
    """Test default retryable exceptions."""

    def test_connection_error_is_retryable(self):
        """Test ConnectionError is in default list."""
        assert ConnectionError in DEFAULT_RETRYABLE_EXCEPTIONS

    def test_timeout_error_is_retryable(self):
        """Test TimeoutError is in default list."""
        assert TimeoutError in DEFAULT_RETRYABLE_EXCEPTIONS


class TestRetryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_attempts_one_no_retry(self):
        """Test max_attempts=1 means no retries."""
        call_count = 0

        @retry_with_backoff(max_attempts=1, base_delay=0.01)
        def single_attempt():
            nonlocal call_count
            call_count += 1
            raise ConnectionError()

        with pytest.raises(ConnectionError):
            single_attempt()

        assert call_count == 1

    def test_returns_none_correctly(self):
        """Test function returning None works correctly."""
        @retry_with_backoff(max_attempts=2)
        def returns_none():
            return None

        result = returns_none()
        assert result is None

    def test_raises_on_first_attempt_for_non_retryable(self):
        """Test immediate raise for non-retryable on first attempt."""
        @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        def raises_type_error():
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            raises_type_error()
