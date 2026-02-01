"""Integration tests for workflow endpoints.

Tests HTTP layer with mocked services (no real workers/storage).

Pattern:
- Use FastAPI TestClient (real HTTP requests)
- Mock services via app.dependency_overrides
- Test error responses (404, 400, 500)
- Verify HTTP status codes and response structure
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.services.workflow.dependencies import (
    get_intelligent_orchestration_service,
    get_workflow_orchestrator,
    get_workflow_router,
    get_workflow_tracker,
    get_task_repository,
    get_corpus_repository,
    get_workflow_logger,
)
from backend.services.workflow.constants import WORKFLOW_DIARIZATION, WORKFLOW_SOAP


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIXTURES (Mocked Services + TestClient)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def mock_orchestration_service():
    """Mock IntelligentOrchestrationService for /analyze endpoint."""
    service = MagicMock()
    service.orchestrate_intelligent_workflow = AsyncMock(
        return_value={
            "session_id": "test-session-123",
            "status": "dispatched",
            "workflows_dispatched": [WORKFLOW_DIARIZATION, WORKFLOW_SOAP],
            "task_ids": {
                WORKFLOW_DIARIZATION: "task-123",
                WORKFLOW_SOAP: "task-456",
            },
            "routing_decision": {
                "workflows": [WORKFLOW_DIARIZATION, WORKFLOW_SOAP],
                "reasoning": "Audio >60s requires diarization",
                "parallel_execution": True,
                "estimated_cost_usd": 0.00003,
                "estimated_duration_seconds": 120,
            },
            "audio_duration_seconds": 180.5,
            "existing_tasks_skipped": [],
            "cost": {
                "routing_usd": 0.00003,
                "tokens_saved": 1500,
                "savings_usd": 0.0045,
                "net_savings_usd": 0.00447,
            },
            "message": "Intelligent orchestration complete: 2 workflows dispatched.",
        }
    )
    return service


@pytest.fixture
def mock_workflow_orchestrator():
    """Mock WorkflowOrchestrator for simple endpoints."""
    orchestrator = MagicMock()
    orchestrator.dispatch_diarization = AsyncMock(
        return_value={"task_id": "task-123", "status": "dispatched", "estimated_duration_seconds": 60}
    )
    orchestrator.dispatch_soap_generation = AsyncMock(
        return_value={"task_id": "task-456", "status": "dispatched", "estimated_duration_seconds": 90}
    )
    orchestrator.dispatch_emotion_analysis = AsyncMock(
        return_value={"task_id": "task-789", "status": "dispatched", "model_used": "llama3.1:8b"}
    )
    return orchestrator


@pytest.fixture
def client(mock_orchestration_service, mock_workflow_orchestrator):
    """TestClient with mocked services via dependency_overrides.

    Creates simple lambda functions without nested Depends() to avoid
    FastAPI resolving real dependencies before checking overrides.
    """
    # Create simple lambda functions that return mocks directly
    # This bypasses all nested Depends() resolution
    def get_mock_orchestration_service():
        return mock_orchestration_service

    def get_mock_workflow_orchestrator():
        return mock_workflow_orchestrator

    # Override dependencies with simple lambdas
    app.dependency_overrides[get_intelligent_orchestration_service] = get_mock_orchestration_service
    app.dependency_overrides[get_workflow_orchestrator] = get_mock_workflow_orchestrator

    client = TestClient(app)
    yield client

    # Cleanup: Clear overrides after test
    app.dependency_overrides.clear()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: /sessions/{session_id}/analyze (Intelligent Workflow)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_analyze_session_success(client, mock_orchestration_service):
    """Test successful intelligent workflow orchestration."""
    # DEBUG: Print overrides to verify they're registered
    print(f"\n DEBUG: app.dependency_overrides = {app.dependency_overrides}")
    print(f"DEBUG: get_intelligent_orchestration_service in overrides = {get_intelligent_orchestration_service in app.dependency_overrides}")

    response = client.post(
        "/api/workflows/aurity/sessions/test-session-123/analyze",
        params={"language": "es", "user_intent": "quick consult"},
    )

    # Verify HTTP status
    assert response.status_code == 202  # Accepted

    # Verify service was called with correct arguments
    mock_orchestration_service.orchestrate_intelligent_workflow.assert_called_once()
    call_args = mock_orchestration_service.orchestrate_intelligent_workflow.call_args
    assert call_args.kwargs["session_id"] == "test-session-123"
    assert call_args.kwargs["language"] == "es"
    assert call_args.kwargs["user_intent"] == "quick consult"

    # Verify response structure
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["status"] == "dispatched"
    assert WORKFLOW_DIARIZATION in data["workflows_dispatched"]
    assert WORKFLOW_SOAP in data["workflows_dispatched"]
    assert "task_ids" in data
    assert "routing_decision" in data
    assert "cost" in data


def test_analyze_session_audio_not_found(client, mock_orchestration_service):
    """Test 404 error when audio file not found."""
    # Simulate FileNotFoundError
    mock_orchestration_service.orchestrate_intelligent_workflow.side_effect = FileNotFoundError(
        "Audio not found"
    )

    response = client.post("/api/workflows/aurity/sessions/test-session-123/analyze")

    # Verify HTTP 404
    assert response.status_code == 404
    assert "Audio file not found" in response.json()["detail"]


def test_analyze_session_orchestration_failure(client, mock_orchestration_service):
    """Test 500 error when orchestration fails."""
    # Simulate internal error
    mock_orchestration_service.orchestrate_intelligent_workflow.side_effect = Exception("Worker pool full")

    response = client.post("/api/workflows/aurity/sessions/test-session-123/analyze")

    # Verify HTTP 500
    assert response.status_code == 500
    assert "Failed to orchestrate workflows" in response.json()["detail"]


def test_analyze_session_default_language(client, mock_orchestration_service):
    """Test default language parameter (es)."""
    response = client.post("/api/workflows/aurity/sessions/test-session-123/analyze")

    # Verify service received default language
    call_args = mock_orchestration_service.orchestrate_intelligent_workflow.call_args
    assert call_args.kwargs["language"] == "es"  # Default


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: /sessions/{session_id}/diarization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_diarization_success(client, mock_workflow_orchestrator):
    """Test successful diarization dispatch."""
    response = client.post("/api/workflows/aurity/sessions/test-session-123/diarization")

    # Verify HTTP status
    assert response.status_code == 202  # Accepted

    # Verify orchestrator was called
    mock_workflow_orchestrator.dispatch_diarization.assert_called_once()
    call_args = mock_workflow_orchestrator.dispatch_diarization.call_args
    assert call_args.kwargs["session_id"] == "test-session-123"

    # Verify response structure
    data = response.json()
    assert data["task_id"] == "task-123"
    assert data["status"] == "dispatched"


def test_diarization_audio_not_found(client, mock_workflow_orchestrator):
    """Test 404 error when audio file not found."""
    mock_workflow_orchestrator.dispatch_diarization.side_effect = FileNotFoundError("Audio not found")

    response = client.post("/api/workflows/aurity/sessions/test-session-123/diarization")

    assert response.status_code == 404
    assert "Audio file not found" in response.json()["detail"]


def test_diarization_invalid_session_id(client):
    """Test 422 error when session_id is invalid."""
    # Invalid session_id (empty string)
    response = client.post("/api/workflows/aurity/sessions//diarization")

    # Verify HTTP 404 (FastAPI path not found)
    assert response.status_code == 404


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: /sessions/{session_id}/soap
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_soap_success(client, mock_workflow_orchestrator):
    """Test successful SOAP generation dispatch."""
    response = client.post("/api/workflows/aurity/sessions/test-session-123/soap")

    # Verify HTTP status
    assert response.status_code == 202

    # Verify orchestrator was called
    mock_workflow_orchestrator.dispatch_soap_generation.assert_called_once()

    # Verify response
    data = response.json()
    assert data["task_id"] == "task-456"
    assert data["status"] == "dispatched"


def test_soap_transcription_not_completed(client, mock_workflow_orchestrator):
    """Test 400 error when transcription not completed yet."""
    mock_workflow_orchestrator.dispatch_soap_generation.side_effect = ValueError(
        "Transcription must be completed first"
    )

    response = client.post("/api/workflows/aurity/sessions/test-session-123/soap")

    assert response.status_code == 400
    assert "Cannot generate SOAP note" in response.json()["detail"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: /sessions/{session_id}/emotion
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_emotion_success(client, mock_workflow_orchestrator):
    """Test successful emotion analysis dispatch."""
    response = client.post("/api/workflows/aurity/sessions/test-session-123/emotion")

    # Verify HTTP status
    assert response.status_code == 202

    # Verify orchestrator was called
    mock_workflow_orchestrator.dispatch_emotion_analysis.assert_called_once()

    # Verify response
    data = response.json()
    assert data["task_id"] == "task-789"
    assert data["status"] == "dispatched"
    assert data["model_used"] == "llama3.1:8b"


def test_emotion_transcription_not_completed(client, mock_workflow_orchestrator):
    """Test 400 error when transcription not completed yet."""
    mock_workflow_orchestrator.dispatch_emotion_analysis.side_effect = ValueError(
        "Transcription must be completed first"
    )

    response = client.post("/api/workflows/aurity/sessions/test-session-123/emotion")

    assert response.status_code == 400
    assert "Cannot analyze emotion" in response.json()["detail"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: Dependency Override Pattern
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_dependency_override_works():
    """Test that dependency_overrides pattern works correctly."""
    # Create custom mock
    custom_service = MagicMock()
    custom_service.orchestrate_intelligent_workflow = AsyncMock(
        return_value={"session_id": "custom", "status": "custom"}
    )

    # Override dependency
    app.dependency_overrides[get_intelligent_orchestration_service] = lambda: custom_service

    # Make request
    client = TestClient(app)
    response = client.post("/api/workflows/aurity/sessions/test-123/analyze")

    # Verify custom mock was called
    custom_service.orchestrate_intelligent_workflow.assert_called_once()
    assert response.json()["status"] == "custom"

    # Cleanup
    app.dependency_overrides.clear()


def test_dependency_override_cleanup():
    """Test that dependency_overrides are cleared after tests."""
    # Verify overrides are empty initially
    assert len(app.dependency_overrides) == 0

    # Add override
    app.dependency_overrides[get_intelligent_orchestration_service] = lambda: MagicMock()

    # Cleanup
    app.dependency_overrides.clear()

    # Verify overrides are empty again
    assert len(app.dependency_overrides) == 0
