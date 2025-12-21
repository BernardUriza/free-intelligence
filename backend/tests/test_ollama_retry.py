"""
Tests for Ollama retry logic with exponential backoff and circuit breaker.

Card: FI-BACKEND-REF-005

Tests:
- Exponential backoff delay calculation
- Circuit breaker state transitions
- Retry decorator behavior
- OllamaProvider retry integration
"""

import pytest
import time
from unittest.mock import Mock

from backend.providers.retry import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    RetryConfig,
    calculate_backoff_delay,
    get_all_circuit_breaker_states,
    get_circuit_breaker,
    reset_circuit_breaker,
    with_retry,
)

# =============================================================================
# Exponential Backoff Tests
# =============================================================================


class TestExponentialBackoff:
    """Test exponential backoff delay calculation."""

    def test_base_delay_first_attempt(self):
        """First attempt should use base delay."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = calculate_backoff_delay(0, config)
        assert delay == 1.0

    def test_exponential_growth(self):
        """Delays should grow exponentially."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        delays = [calculate_backoff_delay(i, config) for i in range(4)]

        assert delays[0] == 1.0  # 1 * 2^0 = 1
        assert delays[1] == 2.0  # 1 * 2^1 = 2
        assert delays[2] == 4.0  # 1 * 2^2 = 4
        assert delays[3] == 8.0  # 1 * 2^3 = 8

    def test_max_delay_cap(self):
        """Delay should be capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)

        delay = calculate_backoff_delay(10, config)  # Would be 1024 without cap

        assert delay == 5.0

    def test_jitter_adds_variation(self):
        """Jitter should add variation to delays."""
        config = RetryConfig(base_delay=10.0, jitter=True)

        delays = [calculate_backoff_delay(0, config) for _ in range(20)]

        # With jitter, delays should vary (not all identical)
        assert len(set(delays)) > 1

        # All should be within ±25% of base
        for d in delays:
            assert 7.5 <= d <= 12.5

    def test_minimum_delay_floor(self):
        """Delay should never go below minimum (100ms)."""
        config = RetryConfig(base_delay=0.01, jitter=True)

        delays = [calculate_backoff_delay(0, config) for _ in range(10)]

        for d in delays:
            assert d >= 0.1


# =============================================================================
# Circuit Breaker Tests
# =============================================================================


class TestCircuitBreaker:
    """Test circuit breaker state machine."""

    def test_initial_state_closed(self):
        """Circuit should start in CLOSED state."""
        cb = CircuitBreaker(name="test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        """Circuit should open after failure threshold is reached."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)

        # Record failures
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()

        # Should now be open
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_success_resets_failure_count(self):
        """Success should reset failure count in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(name="test", config=config)

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0

    def test_half_open_after_recovery_timeout(self):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker(name="test", config=config)

        # Open the circuit
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should now be HALF_OPEN
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        """Circuit should close from HALF_OPEN after success threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        cb = CircuitBreaker(name="test", config=config)

        # Open and wait for half-open
        cb.record_failure()
        time.sleep(0.15)
        cb.can_execute()  # Transitions to HALF_OPEN

        assert cb.state == CircuitState.HALF_OPEN

        # Record successes
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()

        # Should now be CLOSED
        assert cb.state == CircuitState.CLOSED

    def test_half_open_reopens_on_failure(self):
        """Circuit should reopen immediately on failure during HALF_OPEN."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)
        cb = CircuitBreaker(name="test", config=config)

        # Open and wait for half-open
        cb.record_failure()
        time.sleep(0.15)
        cb.can_execute()

        assert cb.state == CircuitState.HALF_OPEN

        # Failure during half-open
        cb.record_failure()

        # Should reopen immediately
        assert cb.state == CircuitState.OPEN

    def test_get_state_info(self):
        """Should return complete state information."""
        cb = CircuitBreaker(name="test_info")
        cb.record_failure()

        info = cb.get_state_info()

        assert info["name"] == "test_info"
        assert info["state"] == "closed"
        assert info["failure_count"] == 1
        assert "config" in info


# =============================================================================
# Circuit Breaker Registry Tests
# =============================================================================


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functions."""

    def test_get_circuit_breaker_creates_new(self):
        """get_circuit_breaker should create new instance if not exists."""
        cb = get_circuit_breaker("new_test_cb")
        assert cb.name == "new_test_cb"
        assert cb.state == CircuitState.CLOSED

    def test_get_circuit_breaker_returns_existing(self):
        """get_circuit_breaker should return same instance for same name."""
        cb1 = get_circuit_breaker("same_name_cb")
        cb2 = get_circuit_breaker("same_name_cb")
        assert cb1 is cb2

    def test_reset_circuit_breaker(self):
        """reset_circuit_breaker should reset state to CLOSED."""
        cb = get_circuit_breaker("reset_test_cb")
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()

        assert cb.state == CircuitState.OPEN

        reset_circuit_breaker("reset_test_cb")

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_get_all_states(self):
        """get_all_circuit_breaker_states should return all states."""
        get_circuit_breaker("state_test_1")
        get_circuit_breaker("state_test_2")

        states = get_all_circuit_breaker_states()

        assert "state_test_1" in states
        assert "state_test_2" in states


# =============================================================================
# Retry Decorator Tests
# =============================================================================


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_no_retry_on_success(self):
        """Should not retry on successful call."""
        call_count = 0

        @with_retry(retry_config=RetryConfig(max_retries=3))
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        """Should retry on failure up to max_retries."""
        call_count = 0

        @with_retry(retry_config=RetryConfig(max_retries=3, base_delay=0.01))
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("test error")

        with pytest.raises(ValueError):
            failing_func()

        # Initial + 3 retries = 4 total attempts
        assert call_count == 4

    def test_succeeds_after_retry(self):
        """Should succeed if retry eventually works."""
        call_count = 0

        @with_retry(retry_config=RetryConfig(max_retries=3, base_delay=0.01))
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "success"

        result = sometimes_fails()

        assert result == "success"
        assert call_count == 3

    def test_circuit_breaker_blocks_when_open(self):
        """Should raise CircuitOpenError when circuit is open."""
        cb = CircuitBreaker(
            name="decorator_test",
            config=CircuitBreakerConfig(failure_threshold=1),
        )
        cb.record_failure()  # Open the circuit

        @with_retry(circuit_breaker=cb)
        def blocked_func():
            return "never called"

        with pytest.raises(CircuitOpenError):
            blocked_func()

    def test_specific_exceptions_only(self):
        """Should only retry specified exception types."""
        call_count = 0

        @with_retry(
            retry_config=RetryConfig(max_retries=3, base_delay=0.01),
            retryable_exceptions=(ValueError,),
        )
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            raises_type_error()

        # Should not retry for non-retryable exception
        assert call_count == 1


# =============================================================================
# OllamaProvider Integration Tests
# =============================================================================


class TestOllamaProviderRetry:
    """Test OllamaProvider with retry integration."""

    def test_ollama_retries_on_connection_error(self):
        """OllamaProvider should retry on connection errors."""
        # Skip if ollama is not installed
        pytest.importorskip("ollama")

        from backend.providers.llm import OllamaProvider
        from backend.providers.retry import reset_circuit_breaker

        # Reset circuit breaker
        reset_circuit_breaker("ollama_http://localhost:11434")

        call_count = 0

        def mock_chat(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return {
                "message": {"content": "success"},
                "eval_count": 10,
                "prompt_eval_count": 5,
            }

        provider = OllamaProvider({"max_retries": 3, "retry_base_delay": 0.01})

        # Patch the client's chat method directly
        provider.client.chat = mock_chat

        response = provider.generate("test prompt")

        assert response.content == "success"
        assert call_count == 3  # 2 failures + 1 success

    def test_ollama_circuit_breaker_opens(self):
        """OllamaProvider circuit breaker should open after threshold failures."""
        pytest.importorskip("ollama")

        from backend.providers.llm import OllamaProvider
        from backend.providers.retry import CircuitOpenError

        # Use unique base_url to get fresh circuit breaker
        unique_url = f"http://localhost:11434/test_{time.time()}"

        provider = OllamaProvider(
            {
                "base_url": unique_url,
                "max_retries": 1,
                "retry_base_delay": 0.01,
                "circuit_failure_threshold": 3,  # Low threshold for testing
            }
        )

        # Verify we have the right threshold
        assert provider.circuit_breaker.config.failure_threshold == 3

        # Patch client to always fail
        provider.client.chat = Mock(side_effect=ConnectionError("Connection refused"))

        # First call: fails and records failures (initial + 1 retry = 2 failures)
        with pytest.raises(ConnectionError):
            provider.generate("test 1")

        # Second call: 2 more failures (4 total, threshold=3 exceeded after 3)
        with pytest.raises((ConnectionError, CircuitOpenError)):
            provider.generate("test 2")

        # Verify circuit is open (4 failures > threshold of 3)
        assert provider.circuit_breaker.state == CircuitState.OPEN

    def test_ollama_metadata_includes_retry_count(self):
        """Response metadata should include retry attempt count."""
        pytest.importorskip("ollama")

        from backend.providers.llm import OllamaProvider
        from backend.providers.retry import reset_circuit_breaker

        reset_circuit_breaker("ollama_http://localhost:11434")

        call_count = 0

        def mock_chat(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection refused")
            return {
                "message": {"content": "success"},
                "eval_count": 10,
            }

        provider = OllamaProvider({"max_retries": 3, "retry_base_delay": 0.01})
        provider.client.chat = mock_chat

        response = provider.generate("test prompt")

        assert response.metadata is not None
        assert response.metadata["retry_attempts"] == 1  # Succeeded on 2nd attempt


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for retry + circuit breaker."""

    def test_full_failure_recovery_cycle(self):
        """Test complete failure → recovery cycle."""
        cb = CircuitBreaker(
            name="integration_test_unique",  # Unique name to avoid conflicts
            config=CircuitBreakerConfig(
                failure_threshold=3,  # Higher threshold to account for retries
                recovery_timeout=0.1,
                success_threshold=1,
            ),
        )

        call_count = 0
        failure_mode = True

        @with_retry(
            retry_config=RetryConfig(max_retries=0, base_delay=0.01),  # No retries for simplicity
            circuit_breaker=cb,
        )
        def api_call():
            nonlocal call_count
            call_count += 1
            if failure_mode:
                raise ValueError("service unavailable")
            return "success"

        # Phase 1: Failures open the circuit (need 3 failures)
        with pytest.raises(ValueError):
            api_call()
        with pytest.raises(ValueError):
            api_call()
        with pytest.raises(ValueError):
            api_call()

        assert cb.state == CircuitState.OPEN

        # Phase 2: Circuit is open, calls rejected
        with pytest.raises(CircuitOpenError):
            api_call()

        # Phase 3: Wait for recovery timeout
        time.sleep(0.15)

        # Phase 4: Service recovers
        failure_mode = False
        result = api_call()

        assert result == "success"
        assert cb.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
