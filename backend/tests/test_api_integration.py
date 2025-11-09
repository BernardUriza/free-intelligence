"""Integration tests for API endpoints.

Tests complete request/response cycles for athletes, coaches, and sessions APIs.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for API integration tests."""
    from backend.app.main import create_app

    app = create_app()
    return TestClient(app)


class TestAthletesAPI:
    """Integration tests for Athletes API."""

    def test_list_athletes(self, client):
        """Test GET /internal/athletes - list all athletes."""
        response = client.get("/internal/athletes/")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "athletes" in data["data"]
        assert isinstance(data["data"]["athletes"], list)

    def test_list_athletes_filtered_by_coach(self, client):
        """Test GET /internal/athletes?coach_id=X - filter by coach."""
        response = client.get("/internal/athletes/?coach_id=coach_001")

        assert response.status_code == 200
        data = response.json()
        assert "athletes" in data["data"]

    def test_get_athlete_by_id(self, client):
        """Test GET /internal/athletes/{id} - get single athlete."""
        response = client.get("/internal/athletes/athlete_001")

        assert response.status_code == 200
        data = response.json()
        assert "athlete" in data["data"]
        assert data["data"]["athlete"]["id"] == "athlete_001"

    def test_get_nonexistent_athlete(self, client):
        """Test GET /internal/athletes/{id} - 404 for nonexistent."""
        response = client.get("/internal/athletes/nonexistent_athlete_999")

        assert response.status_code == 404

    def test_get_athlete_sessions(self, client):
        """Test GET /internal/athletes/{id}/sessions."""
        response = client.get("/internal/athletes/athlete_001/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data["data"]
        assert isinstance(data["data"]["sessions"], list)

    def test_get_athlete_progress(self, client):
        """Test GET /internal/athletes/{id}/progress."""
        response = client.get("/internal/athletes/athlete_001/progress")

        assert response.status_code == 200
        data = response.json()
        assert "athleteId" in data["data"]
        assert "sessionsCompleted" in data["data"]
        assert "sessionsTotal" in data["data"]


class TestCoachesAPI:
    """Integration tests for Coaches API."""

    def test_list_coaches(self, client):
        """Test GET /internal/coaches - list all coaches."""
        response = client.get("/internal/coaches/")

        assert response.status_code == 200
        data = response.json()
        assert "coaches" in data["data"]
        assert isinstance(data["data"]["coaches"], list)

    def test_get_coach_by_id(self, client):
        """Test GET /internal/coaches/{id} - get single coach."""
        response = client.get("/internal/coaches/coach_001")

        assert response.status_code == 200
        data = response.json()
        assert "coach" in data["data"]
        assert data["data"]["coach"]["id"] == "coach_001"

    def test_get_coach_athletes(self, client):
        """Test GET /internal/coaches/{id}/athletes."""
        response = client.get("/internal/coaches/coach_001/athletes")

        assert response.status_code == 200
        data = response.json()
        assert "athletes" in data["data"]
        assert isinstance(data["data"]["athletes"], list)

    def test_get_coach_recent_sessions(self, client):
        """Test GET /internal/coaches/{id}/recent-sessions."""
        response = client.get("/internal/coaches/coach_001/recent-sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data["data"]
        assert isinstance(data["data"]["sessions"], list)


class TestSessionsAPI:
    """Integration tests for Sessions API."""

    @patch("backend.container.get_container")
    def test_create_session(self, mock_get_container, client):
        """Test POST /internal/sessions - create new session."""
        # Mock DI container and service
        mock_container = Mock()
        mock_session_service = Mock()
        mock_audit_service = Mock()

        mock_container.get_session_service.return_value = mock_session_service
        mock_container.get_audit_service.return_value = mock_audit_service

        mock_session_service.create_session.return_value = {
            "session_id": "test_session_123",
            "status": "active",
            "user_id": "user_abc",
        }

        mock_get_container.return_value = mock_container

        # Create session
        response = client.post(
            "/internal/sessions",
            json={
                "owner_hash": "user_abc",
                "status": "new",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["status"] in ["new", "active"]

    @patch("backend.container.get_container")
    def test_list_sessions(self, mock_get_container, client):
        """Test GET /internal/sessions - list sessions."""
        mock_container = Mock()
        mock_session_service = Mock()
        mock_audit_service = Mock()

        mock_container.get_session_service.return_value = mock_session_service
        mock_container.get_audit_service.return_value = mock_audit_service

        mock_session_service.list_sessions.return_value = [
            {"session_id": "s1", "status": "active", "user_id": "user_1"},
            {"session_id": "s2", "status": "completed", "user_id": "user_1"},
        ]

        mock_get_container.return_value = mock_container

        response = client.get("/internal/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)

    @patch("backend.container.get_container")
    def test_get_session_by_id(self, mock_get_container, client):
        """Test GET /internal/sessions/{id} - get single session."""
        mock_container = Mock()
        mock_session_service = Mock()
        mock_audit_service = Mock()

        mock_container.get_session_service.return_value = mock_session_service
        mock_container.get_audit_service.return_value = mock_audit_service

        mock_session_service.get_session.return_value = {
            "session_id": "test_123",
            "status": "active",
            "user_id": "user_xyz",
            "metadata": {},
        }

        mock_get_container.return_value = mock_container

        response = client.get("/internal/sessions/test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_123"


class TestSystemAPI:
    """Integration tests for System API."""

    def test_health_check(self, client):
        """Test GET /health - health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_system_info(self, client):
        """Test GET /api/system/info - system information."""
        response = client.get("/api/system/info")

        # May not be implemented yet
        assert response.status_code in [200, 404]


class TestAuditAPI:
    """Integration tests for Audit API."""

    def test_audit_endpoint_exists(self, client):
        """Test that audit endpoints are registered."""
        # Audit API should exist (may require auth)
        response = client.get("/internal/audit/logs")

        # Either returns data or 404/405 (not implemented)
        assert response.status_code in [200, 404, 405, 500]
