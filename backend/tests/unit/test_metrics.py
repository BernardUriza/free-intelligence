"""Unit tests for metrics module.

Tests Prometheus metrics and decorators.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from backend.utils.metrics import (
    circuit_breaker_rejections_total,
    circuit_breaker_state,
    circuit_breaker_transitions_total,
    hdf5_operation_duration_seconds,
    hdf5_operations_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    idempotency_cache_hits_total,
    idempotency_cache_misses_total,
    idempotency_cache_size,
    llm_request_duration_seconds,
    llm_requests_in_progress,
    llm_requests_total,
    llm_tokens_total,
    retry_attempts_total,
    retry_exhausted_total,
    retry_successes_total,
    session_files_size_bytes,
    session_files_total,
    setup_metrics_endpoint,
    track_llm_request,
    track_workflow_task,
    workflow_completions_total,
    workflow_task_duration_seconds,
    workflow_tasks_in_progress,
    workflow_tasks_total,
)


class TestMetricsExist:
    """Tests that all metrics are properly defined."""

    def test_http_metrics_exist(self) -> None:
        """HTTP metrics are defined."""
        assert http_requests_total is not None
        assert http_request_duration_seconds is not None
        assert http_requests_in_progress is not None

    def test_workflow_metrics_exist(self) -> None:
        """Workflow metrics are defined."""
        assert workflow_tasks_total is not None
        assert workflow_task_duration_seconds is not None
        assert workflow_tasks_in_progress is not None
        assert workflow_completions_total is not None

    def test_llm_metrics_exist(self) -> None:
        """LLM metrics are defined."""
        assert llm_requests_total is not None
        assert llm_request_duration_seconds is not None
        assert llm_tokens_total is not None
        assert llm_requests_in_progress is not None

    def test_circuit_breaker_metrics_exist(self) -> None:
        """Circuit breaker metrics are defined."""
        assert circuit_breaker_state is not None
        assert circuit_breaker_transitions_total is not None
        assert circuit_breaker_rejections_total is not None

    def test_storage_metrics_exist(self) -> None:
        """Storage metrics are defined."""
        assert hdf5_operations_total is not None
        assert hdf5_operation_duration_seconds is not None
        assert session_files_total is not None
        assert session_files_size_bytes is not None

    def test_idempotency_metrics_exist(self) -> None:
        """Idempotency metrics are defined."""
        assert idempotency_cache_hits_total is not None
        assert idempotency_cache_misses_total is not None
        assert idempotency_cache_size is not None

    def test_retry_metrics_exist(self) -> None:
        """Retry metrics are defined."""
        assert retry_attempts_total is not None
        assert retry_successes_total is not None
        assert retry_exhausted_total is not None


class TestTrackWorkflowTask:
    """Tests for track_workflow_task decorator."""

    def test_decorator_returns_callable(self) -> None:
        """Decorator returns callable."""
        decorator = track_workflow_task("TEST_TASK")
        assert callable(decorator)

    def test_decorated_function_executes(self) -> None:
        """Decorated function executes normally."""

        @track_workflow_task("TEST_TASK")
        def sample_task() -> str:
            return "completed"

        result = sample_task()
        assert result == "completed"

    def test_decorated_function_with_args(self) -> None:
        """Decorated function passes arguments through."""

        @track_workflow_task("TEST_TASK")
        def sample_task(a: int, b: int) -> int:
            return a + b

        result = sample_task(2, 3)
        assert result == 5

    def test_decorated_function_with_kwargs(self) -> None:
        """Decorated function passes kwargs through."""

        @track_workflow_task("TEST_TASK")
        def sample_task(*, value: str) -> str:
            return value.upper()

        result = sample_task(value="test")
        assert result == "TEST"

    def test_decorated_function_exception_propagates(self) -> None:
        """Exceptions from decorated function propagate."""

        @track_workflow_task("FAILING_TASK")
        def failing_task() -> None:
            raise ValueError("Task failed")

        with pytest.raises(ValueError, match="Task failed"):
            failing_task()

    def test_preserves_function_name(self) -> None:
        """Decorator preserves function name."""

        @track_workflow_task("TEST_TASK")
        def my_special_task() -> None:
            pass

        assert my_special_task.__name__ == "my_special_task"


class TestTrackLlmRequest:
    """Tests for track_llm_request decorator."""

    def test_decorator_returns_callable(self) -> None:
        """Decorator returns callable."""
        decorator = track_llm_request("claude", "sonnet")
        assert callable(decorator)

    def test_decorated_function_executes(self) -> None:
        """Decorated function executes normally."""

        @track_llm_request("openai", "gpt-4")
        def call_api() -> str:
            return "response"

        result = call_api()
        assert result == "response"

    def test_decorated_function_with_args(self) -> None:
        """Decorated function passes arguments through."""

        @track_llm_request("anthropic", "claude-3")
        def call_api(prompt: str) -> str:
            return f"Response to: {prompt}"

        result = call_api("Hello")
        assert result == "Response to: Hello"

    def test_decorated_function_exception_propagates(self) -> None:
        """Exceptions from decorated function propagate."""

        @track_llm_request("failing", "model")
        def failing_api() -> None:
            raise ConnectionError("API error")

        with pytest.raises(ConnectionError, match="API error"):
            failing_api()

    def test_preserves_function_name(self) -> None:
        """Decorator preserves function name."""

        @track_llm_request("provider", "model")
        def my_llm_function() -> None:
            pass

        assert my_llm_function.__name__ == "my_llm_function"


class TestSetupMetricsEndpoint:
    """Tests for setup_metrics_endpoint function."""

    def test_adds_metrics_route(self) -> None:
        """Adds /metrics route to app."""
        mock_app = MagicMock()
        setup_metrics_endpoint(mock_app)

        # Check that get decorator was called with "/metrics"
        mock_app.get.assert_called_once_with("/metrics")

    def test_endpoint_returns_prometheus_format(self) -> None:
        """Metrics endpoint returns Prometheus format."""
        # This is an integration-like test
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        setup_metrics_endpoint(app)

        client = TestClient(app)
        response = client.get("/metrics")

        assert response.status_code == 200
        # Prometheus metrics contain these headers
        assert "text/plain" in response.headers["content-type"] or "openmetrics" in response.headers["content-type"]
        # Should contain some metric content
        assert "http_requests_total" in response.text or "workflow_tasks_total" in response.text or len(response.text) > 0
