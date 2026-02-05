"""Extended unit tests for retry module.

Tests for retry logic, circuit breaker, and exponential backoff functionality.
"""

from __future__ import annotations

import time

import pytest

# ==============================================================================
# CIRCUIT STATE ENUM TESTS
# ==============================================================================


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_circuit_state_values(self) -> None:
        """Test CircuitState enum values."""
        from backend.providers.retry import CircuitState

        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


# ==============================================================================
# CIRCUIT BREAKER CONFIG TESTS
# ==============================================================================


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_config_defaults(self) -> None:
        """Test CircuitBreakerConfig default values."""
        from backend.providers.retry import CircuitBreakerConfig

        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 2

    def test_config_custom_values(self) -> None:
        """Test CircuitBreakerConfig with custom values."""
        from backend.providers.retry import CircuitBreakerConfig

        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=1,
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.success_threshold == 1

    def test_config_to_dict(self) -> None:
        """Test CircuitBreakerConfig.to_dict()."""
        from backend.providers.retry import CircuitBreakerConfig

        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120.0,
            success_threshold=3,
        )
        result = config.to_dict()

        assert result == {
            "failure_threshold": 10,
            "recovery_timeout": 120.0,
            "success_threshold": 3,
        }


# ==============================================================================
# RETRY CONFIG TESTS
# ==============================================================================


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_retry_config_defaults(self) -> None:
        """Test RetryConfig default values."""
        from backend.providers.retry import RetryConfig

        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_retry_config_custom_values(self) -> None:
        """Test RetryConfig with custom values."""
        from backend.providers.retry import RetryConfig

        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_retry_config_to_dict(self) -> None:
        """Test RetryConfig.to_dict()."""
        from backend.providers.retry import RetryConfig

        config = RetryConfig(
            max_retries=2,
            base_delay=2.0,
            max_delay=10.0,
            exponential_base=2.5,
            jitter=True,
        )
        result = config.to_dict()

        assert result == {
            "max_retries": 2,
            "base_delay": 2.0,
            "max_delay": 10.0,
            "exponential_base": 2.5,
            "jitter": True,
        }


# ==============================================================================
# CIRCUIT BREAKER TESTS
# ==============================================================================


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_circuit_breaker_initial_state(self) -> None:
        """Test CircuitBreaker starts in closed state."""
        from backend.providers.retry import CircuitBreaker

        cb = CircuitBreaker(name="test")

        assert cb.name == "test"
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.last_failure_time is None

    def test_circuit_breaker_can_execute_closed(self) -> None:
        """Test can_execute returns True when closed."""
        from backend.providers.retry import CircuitBreaker

        cb = CircuitBreaker(name="test")

        assert cb.can_execute() is True

    def test_circuit_breaker_record_success_resets_failures(self) -> None:
        """Test record_success resets failure count."""
        from backend.providers.retry import CircuitBreaker

        cb = CircuitBreaker(name="test")
        cb.failure_count = 3

        cb.record_success()

        assert cb.failure_count == 0

    def test_circuit_breaker_opens_after_threshold(self) -> None:
        """Test circuit opens after reaching failure threshold."""
        from backend.providers.retry import CircuitBreaker, CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)

        # Record failures up to threshold
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()  # Should open now
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_circuit_breaker_half_open_after_timeout(self) -> None:
        """Test circuit transitions to half-open after recovery timeout."""
        from backend.providers.retry import CircuitBreaker, CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker(name="test", config=config)

        # Open the circuit
        cb.record_failure()
        assert cb.state == "open"

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should transition to half-open
        assert cb.can_execute() is True
        assert cb.state == "half_open"

    def test_circuit_breaker_closes_from_half_open(self) -> None:
        """Test circuit closes from half-open after successes."""
        from backend.providers.retry import CircuitBreaker, CircuitBreakerConfig

        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        cb = CircuitBreaker(name="test", config=config)

        # Open the circuit and wait for half-open
        cb.record_failure()
        time.sleep(0.15)
        cb.can_execute()  # Transition to half-open
        assert cb.state == "half_open"

        # Record successes
        cb.record_success()
        assert cb.state == "half_open"  # Not enough yet
        cb.record_success()
        assert cb.state == "closed"  # Now closed

    def test_circuit_breaker_reopens_from_half_open_on_failure(self) -> None:
        """Test circuit reopens from half-open on failure."""
        from backend.providers.retry import CircuitBreaker, CircuitBreakerConfig

        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker(name="test", config=config)

        # Open and transition to half-open
        cb.record_failure()
        time.sleep(0.15)
        cb.can_execute()
        assert cb.state == "half_open"

        # Failure during half-open should reopen
        cb.record_failure()
        assert cb.state == "open"

    def test_circuit_breaker_get_state_info(self) -> None:
        """Test get_state_info returns correct structure."""
        from backend.providers.retry import CircuitBreaker, CircuitBreakerConfig

        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=2,
        )
        cb = CircuitBreaker(name="test-service", config=config)
        cb.failure_count = 2

        info = cb.get_state_info()

        assert info["name"] == "test-service"
        assert info["state"] == "closed"
        assert info["failure_count"] == 2
        assert info["success_count"] == 0
        assert info["last_failure_time"] is None
        assert info["config"]["failure_threshold"] == 5
        assert info["config"]["recovery_timeout"] == 60.0
        assert info["config"]["success_threshold"] == 2


# ==============================================================================
# CIRCUIT OPEN ERROR TESTS
# ==============================================================================


class TestCircuitOpenError:
    """Tests for CircuitOpenError exception."""

    def test_circuit_open_error_creation(self) -> None:
        """Test CircuitOpenError creation."""
        from backend.providers.retry import CircuitOpenError

        error = CircuitOpenError("api-service")

        assert error.name == "api-service"
        assert str(error) == "api-service: Circuit breaker is open"

    def test_circuit_open_error_custom_message(self) -> None:
        """Test CircuitOpenError with custom message."""
        from backend.providers.retry import CircuitOpenError

        error = CircuitOpenError("api-service", "Service unavailable")

        assert str(error) == "api-service: Service unavailable"


# ==============================================================================
# CALCULATE BACKOFF DELAY TESTS
# ==============================================================================


class TestCalculateBackoffDelay:
    """Tests for calculate_backoff_delay function."""

    def test_backoff_delay_first_attempt(self) -> None:
        """Test delay for first attempt (attempt=0)."""
        from backend.providers.retry import RetryConfig, calculate_backoff_delay

        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        delay = calculate_backoff_delay(0, config)

        assert delay == 1.0

    def test_backoff_delay_exponential_growth(self) -> None:
        """Test exponential growth of delay."""
        from backend.providers.retry import RetryConfig, calculate_backoff_delay

        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert calculate_backoff_delay(0, config) == 1.0  # 1 * 2^0 = 1
        assert calculate_backoff_delay(1, config) == 2.0  # 1 * 2^1 = 2
        assert calculate_backoff_delay(2, config) == 4.0  # 1 * 2^2 = 4
        assert calculate_backoff_delay(3, config) == 8.0  # 1 * 2^3 = 8

    def test_backoff_delay_max_cap(self) -> None:
        """Test delay is capped at max_delay."""
        from backend.providers.retry import RetryConfig, calculate_backoff_delay

        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )

        # Should be capped at 5.0, not 8.0
        delay = calculate_backoff_delay(3, config)

        assert delay == 5.0

    def test_backoff_delay_with_jitter(self) -> None:
        """Test delay with jitter adds randomness."""
        from backend.providers.retry import RetryConfig, calculate_backoff_delay

        config = RetryConfig(base_delay=4.0, exponential_base=1.0, jitter=True)

        # Run multiple times and check variation
        delays = [calculate_backoff_delay(0, config) for _ in range(20)]

        # Should have some variation (±25% of 4.0 = 3.0 to 5.0)
        assert min(delays) >= 3.0
        assert max(delays) <= 5.0
        # Not all delays should be identical
        assert len(set(delays)) > 1

    def test_backoff_delay_minimum(self) -> None:
        """Test delay has minimum of 0.1 seconds."""
        from backend.providers.retry import RetryConfig, calculate_backoff_delay

        config = RetryConfig(base_delay=0.01, exponential_base=1.0, jitter=False)

        delay = calculate_backoff_delay(0, config)

        assert delay >= 0.1


# ==============================================================================
# WITH_RETRY DECORATOR TESTS
# ==============================================================================


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""

    def test_with_retry_success_first_try(self) -> None:
        """Test with_retry succeeds on first try."""
        from backend.providers.retry import RetryConfig, with_retry

        call_count = 0

        @with_retry(retry_config=RetryConfig(max_retries=3))
        def successful_function() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_with_retry_retries_on_failure(self) -> None:
        """Test with_retry retries on failure."""
        from backend.providers.retry import RetryConfig, with_retry

        call_count = 0

        @with_retry(retry_config=RetryConfig(max_retries=3, base_delay=0.01))
        def failing_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_then_success()

        assert result == "success"
        assert call_count == 3

    def test_with_retry_exhausts_retries(self) -> None:
        """Test with_retry raises after exhausting retries."""
        from backend.providers.retry import RetryConfig, with_retry

        call_count = 0

        @with_retry(retry_config=RetryConfig(max_retries=2, base_delay=0.01))
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

        # Initial + 2 retries = 3 calls
        assert call_count == 3

    def test_with_retry_respects_retryable_exceptions(self) -> None:
        """Test with_retry only retries specified exceptions."""
        from backend.providers.retry import RetryConfig, with_retry

        call_count = 0

        @with_retry(
            retry_config=RetryConfig(max_retries=3, base_delay=0.01),
            retryable_exceptions=(ValueError,),
        )
        def raises_type_error() -> str:
            nonlocal call_count
            call_count += 1
            raise TypeError("Non-retryable")

        with pytest.raises(TypeError):
            raises_type_error()

        # Should not retry - only 1 call
        assert call_count == 1

    def test_with_retry_with_circuit_breaker(self) -> None:
        """Test with_retry integrates with circuit breaker."""
        from backend.providers.retry import (
            CircuitBreaker,
            CircuitBreakerConfig,
            RetryConfig,
            with_retry,
        )

        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=2),
        )

        @with_retry(
            retry_config=RetryConfig(max_retries=1, base_delay=0.01),
            circuit_breaker=cb,
        )
        def always_fails() -> str:
            raise ValueError("Fails")

        # First call - will retry once then fail
        with pytest.raises(ValueError):
            always_fails()

        # Circuit should now be open (2 failures)
        assert cb.state == "open"

    def test_with_retry_circuit_breaker_blocks_call(self) -> None:
        """Test with_retry blocks call when circuit is open."""
        from backend.providers.retry import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitOpenError,
            RetryConfig,
            with_retry,
        )

        cb = CircuitBreaker(
            name="test",
            config=CircuitBreakerConfig(failure_threshold=1),
        )
        # Open the circuit
        cb.record_failure()
        assert cb.state == "open"

        @with_retry(
            retry_config=RetryConfig(max_retries=3),
            circuit_breaker=cb,
        )
        def blocked_function() -> str:
            return "should not reach"

        with pytest.raises(CircuitOpenError, match="Service unavailable"):
            blocked_function()

    def test_with_retry_records_success_to_circuit_breaker(self) -> None:
        """Test with_retry records success to circuit breaker."""
        from backend.providers.retry import CircuitBreaker, RetryConfig, with_retry

        cb = CircuitBreaker(name="test")
        cb.failure_count = 3  # Some prior failures

        @with_retry(
            retry_config=RetryConfig(max_retries=3),
            circuit_breaker=cb,
        )
        def successful() -> str:
            return "ok"

        successful()

        # Success should reset failure count
        assert cb.failure_count == 0
