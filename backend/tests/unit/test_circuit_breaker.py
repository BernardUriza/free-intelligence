"""Tests for Circuit Breaker pattern implementation.

Coverage target: 100% of backend/utils/circuit_breaker.py
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from backend.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerCallResult,
    CircuitBreakerOpen,
    CircuitState,
    circuit_breaker,
    get_all_circuit_breakers,
    get_circuit_breaker,
)


class TestCircuitState:
    """Test CircuitState enum."""

    def test_state_values(self):
        """Test all states exist with correct values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerOpen:
    """Test CircuitBreakerOpen exception."""

    def test_exception_message(self):
        """Test exception contains service name and retry time."""
        exc = CircuitBreakerOpen("deepgram", 30.5)
        assert exc.service_name == "deepgram"
        assert exc.retry_after == 30.5
        assert "deepgram" in str(exc)
        assert "30.5" in str(exc)

    def test_exception_is_raisable(self):
        """Test exception can be raised and caught."""
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            raise CircuitBreakerOpen("test_service", 10.0)
        
        assert exc_info.value.service_name == "test_service"


class TestCircuitBreakerCallResult:
    """Test CircuitBreakerCallResult dataclass."""

    def test_successful_result(self):
        """Test successful call result."""
        result = CircuitBreakerCallResult(
            timestamp=1234567890.0,
            success=True,
            duration_ms=150.5,
        )
        assert result.success is True
        assert result.duration_ms == 150.5
        assert result.exception_type is None

    def test_failed_result(self):
        """Test failed call result."""
        result = CircuitBreakerCallResult(
            timestamp=1234567890.0,
            success=False,
            duration_ms=1000.0,
            exception_type="TimeoutError",
        )
        assert result.success is False
        assert result.exception_type == "TimeoutError"


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Test circuit starts in CLOSED state."""
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED

    def test_successful_call_stays_closed(self):
        """Test successful calls keep circuit CLOSED."""
        breaker = CircuitBreaker(name="test")
        
        def success_func():
            return "success"
        
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    def test_failures_open_circuit(self):
        """Test reaching failure threshold opens circuit."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=60.0,
        )
        
        def failing_func():
            raise ConnectionError("Connection refused")
        
        # Simulate 3 failures
        for i in range(3):
            with pytest.raises(ConnectionError):
                breaker.call(failing_func)
        
        # Circuit should be OPEN now
        assert breaker.state == CircuitState.OPEN

    def test_open_circuit_rejects_calls(self):
        """Test OPEN circuit rejects calls with CircuitBreakerOpen."""
        breaker = CircuitBreaker(
            name="test_reject",
            failure_threshold=2,
            recovery_timeout=60.0,
        )
        
        def failing_func():
            raise ConnectionError()
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker.call(failing_func)
        
        # Next call should be rejected
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            breaker.call(lambda: "should not execute")
        
        assert exc_info.value.service_name == "test_reject"
        assert exc_info.value.retry_after > 0

    def test_recovery_timeout_transitions_to_half_open(self):
        """Test circuit transitions to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(
            name="test_recovery",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast test
        )
        
        def failing_func():
            raise ConnectionError()
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Next call should transition to HALF_OPEN
        result = breaker.call(lambda: "recovered")
        assert result == "recovered"
        # After success, should be CLOSED (or still HALF_OPEN if not enough successes)

    def test_half_open_success_closes_circuit(self):
        """Test successful calls in HALF_OPEN close the circuit."""
        breaker = CircuitBreaker(
            name="test_half_open",
            failure_threshold=2,
            recovery_timeout=0.05,
            success_threshold=2,
        )
        
        def failing_func():
            raise ConnectionError()
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker.call(failing_func)
        
        # Wait for recovery
        time.sleep(0.1)
        
        # First success - still HALF_OPEN
        breaker.call(lambda: "ok")
        
        # Second success - should close
        breaker.call(lambda: "ok")
        
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        """Test failure in HALF_OPEN reopens the circuit."""
        breaker = CircuitBreaker(
            name="test_reopen",
            failure_threshold=2,
            recovery_timeout=0.05,
        )
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        
        # Wait for recovery
        time.sleep(0.1)
        
        # Fail in HALF_OPEN
        with pytest.raises(TimeoutError):
            breaker.call(lambda: (_ for _ in ()).throw(TimeoutError()))
        
        assert breaker.state == CircuitState.OPEN

    def test_excluded_exceptions_not_counted(self):
        """Test excluded exceptions don't count as failures."""
        breaker = CircuitBreaker(
            name="test_excluded",
            failure_threshold=2,
            excluded_exceptions=(ValueError,),
        )
        
        def value_error_func():
            raise ValueError("Not a failure")
        
        # These shouldn't count as failures
        for _ in range(5):
            with pytest.raises(ValueError):
                breaker.call(value_error_func)
        
        # Circuit should still be CLOSED
        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_failure_rate_calculation(self):
        """Test failure rate is calculated correctly."""
        breaker = CircuitBreaker(
            name="test_rate",
            failure_threshold=10,  # High threshold
            window_size=60.0,
        )
        
        # 3 failures
        for _ in range(3):
            with pytest.raises(ConnectionError):
                breaker.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        
        # 2 successes
        for _ in range(2):
            breaker.call(lambda: "ok")
        
        # Failure rate: 3/5 = 0.6
        assert 0.55 <= breaker.failure_rate <= 0.65

    def test_get_stats(self):
        """Test get_stats returns comprehensive information."""
        breaker = CircuitBreaker(name="test_stats")
        
        stats = breaker.get_stats()
        
        assert stats["name"] == "test_stats"
        assert stats["state"] == CircuitState.CLOSED
        assert "failure_threshold" in stats
        assert "recovery_timeout" in stats
        assert "failure_rate" in stats


class TestCircuitBreakerRegistry:
    """Test global circuit breaker registry."""

    def test_get_circuit_breaker_creates_new(self):
        """Test get_circuit_breaker creates new breaker."""
        # Use unique name to avoid conflicts
        name = f"unique_test_{time.time()}"
        breaker = get_circuit_breaker(name=name)
        
        assert breaker.name == name
        assert breaker.state == CircuitState.CLOSED

    def test_get_circuit_breaker_returns_same_instance(self):
        """Test get_circuit_breaker returns same instance for same name."""
        name = f"singleton_test_{time.time()}"
        
        breaker1 = get_circuit_breaker(name=name)
        breaker2 = get_circuit_breaker(name=name)
        
        assert breaker1 is breaker2

    def test_get_all_circuit_breakers(self):
        """Test get_all_circuit_breakers returns all registered."""
        # Create a unique breaker
        name = f"list_test_{time.time()}"
        get_circuit_breaker(name=name)
        
        all_breakers = get_all_circuit_breakers()
        
        assert name in all_breakers
        assert isinstance(all_breakers[name], CircuitBreaker)


class TestCircuitBreakerDecorator:
    """Test @circuit_breaker decorator."""

    def test_decorator_wraps_function(self):
        """Test decorator wraps function correctly."""
        name = f"decorator_test_{time.time()}"
        
        @circuit_breaker(name=name)
        def my_function():
            return "decorated"
        
        result = my_function()
        assert result == "decorated"

    def test_decorator_counts_failures(self):
        """Test decorator counts failures and opens circuit."""
        name = f"decorator_fail_{time.time()}"
        
        @circuit_breaker(name=name, failure_threshold=2)
        def failing_function():
            raise ConnectionError()
        
        # Cause 2 failures
        for _ in range(2):
            with pytest.raises(ConnectionError):
                failing_function()
        
        # Circuit should be open
        with pytest.raises(CircuitBreakerOpen):
            failing_function()

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""
        name = f"metadata_test_{time.time()}"
        
        @circuit_breaker(name=name)
        def well_documented_function():
            """This is the docstring."""
            return True
        
        assert well_documented_function.__name__ == "well_documented_function"
        assert "docstring" in well_documented_function.__doc__


class TestCircuitBreakerThreadSafety:
    """Test thread safety of circuit breaker."""

    def test_concurrent_calls_are_thread_safe(self):
        """Test circuit breaker handles concurrent calls."""
        import threading
        
        name = f"thread_test_{time.time()}"
        breaker = get_circuit_breaker(name=name, failure_threshold=100)
        
        results = []
        errors = []
        
        def call_breaker():
            try:
                result = breaker.call(lambda: "ok")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run 20 concurrent calls
        threads = [threading.Thread(target=call_breaker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed
        assert len(results) == 20
        assert len(errors) == 0
        assert all(r == "ok" for r in results)
