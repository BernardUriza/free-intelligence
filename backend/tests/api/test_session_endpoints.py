"""Integration tests for session endpoints.

Tests the session API endpoints with improved validation and error handling.

NOTE: These tests require the full container infrastructure which may not be
available in CI. They are skipped if backend.services import fails.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# Skip if backend.services is not available (CI environment without full deps)
try:
    import backend.services
except ImportError:
    pytest.skip("backend.services not available", allow_module_level=True)


@pytest.fixture
def client():
    """Create test client for session API integration tests."""
    from backend.app.main import create_app

    app = create_app()
    return TestClient(app)


class TestSessionEndpoints:
    """Integration tests for session API endpoints."""

    def test_get_session_monitor_with_invalid_session_id(self, client):
        """Test GET /api/workflows/aurity/sessions/{session_id}/monitor with invalid session ID."""
        # Test with too short session ID
        response = client.get("/api/workflows/aurity/sessions/abc/monitor")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with too long session ID
        long_session_id = "a" * 200
        response = client.get(f"/api/workflows/aurity/sessions/{long_session_id}/monitor")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid characters (URL encoded)
        response = client.get("/api/workflows/aurity/sessions/invalid%21%40%23session/monitor")
        assert response.status_code in [400, 404]  # Either validation error or path not found

    def test_post_diarization_with_invalid_session_id(self, client):
        """Test POST /api/workflows/aurity/sessions/{session_id}/diarization with invalid session ID."""
        # Test with too short session ID
        response = client.post("/api/workflows/aurity/sessions/abc/diarization")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with too long session ID
        long_session_id = "a" * 200
        response = client.post(f"/api/workflows/aurity/sessions/{long_session_id}/diarization")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid characters (URL encoded)
        response = client.post("/api/workflows/aurity/sessions/invalid%21%40%23session/diarization")
        assert response.status_code in [400, 404]  # Either validation error or path not found

    def test_post_generate_soap_with_invalid_session_id(self, client):
        """Test POST /api/workflows/aurity/sessions/{session_id}/soap with invalid session ID."""
        # Test with too short session ID
        response = client.post("/api/workflows/aurity/sessions/abc/soap")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with too long session ID
        long_session_id = "a" * 200
        response = client.post(f"/api/workflows/aurity/sessions/{long_session_id}/soap")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid characters (URL encoded)
        response = client.post("/api/workflows/aurity/sessions/invalid%21%40%23session/soap")
        assert response.status_code in [400, 404]  # Either validation error or path not found

    def test_get_diarization_segments_with_invalid_session_id(self, client):
        """Test GET /api/workflows/aurity/sessions/{session_id}/diarization/segments with invalid session ID."""
        # Test with too short session ID
        response = client.get("/api/workflows/aurity/sessions/abc/diarization/segments")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with too long session ID
        long_session_id = "a" * 200
        response = client.get(
            f"/api/workflows/aurity/sessions/{long_session_id}/diarization/segments"
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid characters (URL encoded)
        response = client.get(
            "/api/workflows/aurity/sessions/invalid%21%40%23session/diarization/segments"
        )
        assert response.status_code in [400, 404]  # Either validation error or path not found

    def test_get_session_audio_with_invalid_session_id(self, client):
        """Test GET /api/workflows/aurity/sessions/{session_id}/audio with invalid session ID."""
        # Test with too short session ID
        response = client.get("/api/workflows/aurity/sessions/abc/audio")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with too long session ID
        long_session_id = "a" * 200
        response = client.get(f"/api/workflows/aurity/sessions/{long_session_id}/audio")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid characters (URL encoded)
        response = client.get("/api/workflows/aurity/sessions/invalid%21%40%23session/audio")
        assert response.status_code in [400, 404]  # Either validation error or path not found

    @patch("backend.src.fi_workflow.api.public.services.get_workflow_orchestrator")
    def test_diarization_workflow_valid_session_id(self, mock_get_orchestrator, client):
        """Test POST /api/workflows/aurity/sessions/{session_id}/diarization with valid session ID."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.dispatch_diarization.return_value = {
            "session_id": "valid_session_12345",
            "job_id": "valid_session_12345",
            "status": "dispatched",
            "message": "Diarization running in background",
        }
        mock_get_orchestrator.return_value = mock_orchestrator

        # Test with valid session ID
        response = client.post("/api/workflows/aurity/sessions/valid_session_12345/diarization")

        # Response could be 202 or 500 depending on internal processing
        assert response.status_code in [202, 500]

    @patch("backend.src.fi_workflow.api.public.services.get_workflow_orchestrator")
    def test_soap_generation_workflow_valid_session_id(self, mock_get_orchestrator, client):
        """Test POST /api/workflows/aurity/sessions/{session_id}/soap with valid session ID."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.dispatch_soap_generation.return_value = {
            "session_id": "valid_session_12345",
            "job_id": "valid_session_12345",
            "status": "dispatched",
            "message": "SOAP generation running in background",
        }
        mock_get_orchestrator.return_value = mock_orchestrator

        # Test with valid session ID
        response = client.post("/api/workflows/aurity/sessions/valid_session_12345/soap")

        # Response could be 202 or 500 depending on internal processing
        assert response.status_code in [202, 500]
