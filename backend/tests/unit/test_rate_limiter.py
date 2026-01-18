"""Tests for Rate Limiter pattern implementation.

Coverage target: 100% of backend/utils/rate_limiter.py
"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest
from backend.utils.rate_limiter import RateLimiter, azure_whisper_rate_limiter


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_init_sets_parameters(self):
        """Test initialization sets parameters correctly."""
        limiter = RateLimiter(max_calls=5, period_seconds=30.0)
        
        assert limiter.max_calls == 5
        assert limiter.period == 30.0
        assert limiter.calls == []

    def test_first_call_no_wait(self):
        """Test first call doesn't wait."""
        limiter = RateLimiter(max_calls=3, period_seconds=60.0)
        
        waited = limiter.wait_if_needed()
        
        assert waited == 0.0
        assert len(limiter.calls) == 1

    def test_under_limit_no_wait(self):
        """Test calls under limit don't wait."""
        limiter = RateLimiter(max_calls=3, period_seconds=60.0)
        
        # Make 2 calls (under limit of 3)
        limiter.wait_if_needed()
        waited = limiter.wait_if_needed()
        
        assert waited == 0.0
        assert len(limiter.calls) == 2

    def test_at_limit_waits(self):
        """Test calls at limit wait for window to pass."""
        limiter = RateLimiter(max_calls=2, period_seconds=0.1)
        
        # Make 2 calls (at limit)
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # Third call should wait
        start = time.time()
        waited = limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Should have waited approximately 0.1s
        assert waited > 0.05
        assert elapsed >= 0.05

    def test_old_calls_removed_from_window(self):
        """Test old calls outside window are removed."""
        limiter = RateLimiter(max_calls=2, period_seconds=0.05)
        
        # Make 2 calls
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # Wait for window to pass
        time.sleep(0.1)
        
        # Third call should NOT wait (old calls expired)
        waited = limiter.wait_if_needed()
        
        # Might have minimal wait or none
        assert waited < 0.05 or waited == 0.0

    def test_context_manager_entry(self):
        """Test context manager __enter__ calls wait_if_needed."""
        limiter = RateLimiter(max_calls=5, period_seconds=60.0)
        
        with limiter:
            pass
        
        assert len(limiter.calls) == 1

    def test_context_manager_exit_no_exception(self):
        """Test context manager __exit__ handles None."""
        limiter = RateLimiter(max_calls=5, period_seconds=60.0)
        
        with limiter:
            # Normal execution
            result = 1 + 1
        
        assert result == 2

    def test_context_manager_exception_propagates(self):
        """Test context manager propagates exceptions."""
        limiter = RateLimiter(max_calls=5, period_seconds=60.0)
        
        with pytest.raises(ValueError):
            with limiter:
                raise ValueError("Test error")

    def test_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = RateLimiter(max_calls=10, period_seconds=60.0)
        
        results = []
        errors = []
        
        def make_call():
            try:
                limiter.wait_if_needed()
                results.append(True)
            except Exception as e:
                errors.append(e)
        
        # Run 5 concurrent calls
        threads = [threading.Thread(target=make_call) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 5
        assert len(errors) == 0
        assert len(limiter.calls) == 5

    def test_calls_recorded_with_timestamps(self):
        """Test calls are recorded with proper timestamps."""
        limiter = RateLimiter(max_calls=3, period_seconds=60.0)
        
        before = time.time()
        limiter.wait_if_needed()
        after = time.time()
        
        assert len(limiter.calls) == 1
        assert before <= limiter.calls[0] <= after


class TestGlobalRateLimiter:
    """Test global rate limiter instance."""

    def test_azure_whisper_limiter_exists(self):
        """Test deprecated azure_whisper_rate_limiter exists."""
        assert azure_whisper_rate_limiter is not None
        assert isinstance(azure_whisper_rate_limiter, RateLimiter)

    def test_azure_whisper_limiter_config(self):
        """Test azure_whisper_rate_limiter has expected config."""
        assert azure_whisper_rate_limiter.max_calls == 3
        assert azure_whisper_rate_limiter.period == 60.0
