"""
Test suite for Ollama retry logic and circuit breaker.

File: tests/test_ollama_retry.py
Card: FI-CORE-REF-005
Created: 2025-10-29

Tests:
- Exponential backoff retry (2 attempts)
- Circuit breaker opens after threshold failures
- Circuit breaker closes after window expires
- Timeout handling with retry
"""

import time
from unittest.mock import Mock, patch

import pytest
import requests

from backend.llm_adapter import LLMProviderError, LLMRequest
from backend.providers.ollama import OllamaAdapter


class TestOllamaRetry:
    """Test retry logic and exponential backoff."""

    def test_retry_on_timeout(self):
        """Test that adapter retries on timeout."""
        adapter = OllamaAdapter(
            model="test-model",
            max_retries=2,
            timeout_seconds=1,
            base_delay_ms=10,  # Fast retry for tests
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post:
            # First 2 attempts timeout, 3rd succeeds
            mock_post.side_effect = [
                requests.exceptions.Timeout("timeout 1"),
                requests.exceptions.Timeout("timeout 2"),
                Mock(
                    status_code=200,
                    json=lambda: {
                        "response": "success",
                        "eval_count": 10,
                        "prompt_eval_count": 5,
                    },
                ),
            ]

            response = adapter.generate(request)
            assert response.content == "success"
            assert mock_post.call_count == 3

    def test_exponential_backoff_timing(self):
        """Test that backoff delays increase exponentially."""
        adapter = OllamaAdapter(
            model="test-model",
            max_retries=3,
            base_delay_ms=100,
            max_delay_ms=500,
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post, patch("time.sleep") as mock_sleep:
            # All attempts fail
            mock_post.side_effect = requests.exceptions.Timeout("timeout")

            with pytest.raises(LLMProviderError):
                adapter.generate(request)

            # Verify exponential backoff: 100ms, 200ms, 400ms
            # But capped at max_delay_ms=500ms
            assert mock_sleep.call_count == 3
            delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert delays[0] == 0.1  # 100ms
            assert delays[1] == 0.2  # 200ms
            assert delays[2] == 0.4  # 400ms

    def test_max_retries_exceeded(self):
        """Test that adapter fails after max retries."""
        adapter = OllamaAdapter(
            model="test-model",
            max_retries=2,
            base_delay_ms=10,
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("always fails")

            with pytest.raises(LLMProviderError) as exc_info:
                adapter.generate(request)

            assert "failed after 3 attempts" in str(exc_info.value)
            assert mock_post.call_count == 3  # initial + 2 retries


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_opens_after_threshold(self):
        """Test circuit breaker opens after threshold failures."""
        adapter = OllamaAdapter(
            model="test-model",
            circuit_breaker_threshold=3,
            circuit_breaker_window=60,
            max_retries=0,  # Fail immediately for faster tests
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("timeout")

            # Trigger 3 failures (threshold)
            for i in range(3):
                with pytest.raises(LLMProviderError):
                    adapter.generate(request)

            # Circuit should now be open
            assert adapter._is_circuit_open()

            # Next request should fail immediately without calling API
            with pytest.raises(LLMProviderError) as exc_info:
                adapter.generate(request)

            assert "Circuit breaker open" in str(exc_info.value)
            # Should have only 3 calls (not 4), because 4th was blocked
            assert mock_post.call_count == 3

    def test_circuit_closes_after_window(self):
        """Test circuit breaker closes after time window expires."""
        adapter = OllamaAdapter(
            model="test-model",
            circuit_breaker_threshold=2,
            circuit_breaker_window=1,  # 1 second window
            max_retries=0,
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("timeout")

            # Trigger 2 failures (threshold)
            for i in range(2):
                with pytest.raises(LLMProviderError):
                    adapter.generate(request)

            # Circuit should be open
            assert adapter._is_circuit_open()

            # Wait for window to expire
            time.sleep(1.1)

            # Circuit should now be closed
            assert not adapter._is_circuit_open()

    def test_circuit_tracks_failures_in_window(self):
        """Test circuit breaker only counts failures within time window."""
        adapter = OllamaAdapter(
            model="test-model",
            circuit_breaker_threshold=3,
            circuit_breaker_window=1,  # 1 second window
            max_retries=0,
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("timeout")

            # First failure
            with pytest.raises(LLMProviderError):
                adapter.generate(request)

            # Wait for first failure to expire (window + margin)
            time.sleep(1.2)

            # Second failure (first should be expired)
            with pytest.raises(LLMProviderError):
                adapter.generate(request)

            # Circuit should still be closed (only 1 failure in window)
            assert not adapter._is_circuit_open()

            # Only the second failure should be counted now
            assert len(adapter.failure_timestamps) == 1

    def test_circuit_breaker_with_successful_request(self):
        """Test that successful requests don't trigger circuit breaker."""
        adapter = OllamaAdapter(
            model="test-model",
            circuit_breaker_threshold=2,
            circuit_breaker_window=60,
        )

        request = LLMRequest(prompt="test")

        with patch("requests.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "response": "success",
                    "eval_count": 10,
                    "prompt_eval_count": 5,
                },
            )

            # Multiple successful requests
            for i in range(5):
                response = adapter.generate(request)
                assert response.content == "success"

            # Circuit should remain closed
            assert not adapter._is_circuit_open()
            assert len(adapter.failure_timestamps) == 0
