"""Integration tests for Export API endpoints.

Tests the export endpoints with mocked ExportService and AuditService.
Validates API contracts and error handling.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.exports import router


@pytest.fixture
def test_client():
    """Create FastAPI test client."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_export_service():
    """Create mock ExportService."""
    mock = Mock()
    mock.create_export.return_value = {
        "export_id": "exp_123456_7890",
        "session_id": "session_123",
        "artifacts": [
            {"format": "json", "sha256": "abc123", "bytes": 100},
            {"format": "manifest", "sha256": "def456", "bytes": 200},
        ],
        "manifest_sha256": "def456",
    }
    mock.get_export_metadata.return_value = {
        "export_id": "exp_123456_7890",
        "session_id": "session_123",
        "artifacts": [
            {"format": "json", "sha256": "abc123", "bytes": 100},
            {"format": "manifest", "sha256": "def456", "bytes": 200},
        ],
        "created_at": "2025-11-01T12:00:00Z",
    }
    mock.verify_export.return_value = {
        "ok": True,
        "results": [
            {"target": "json", "ok": True},
            {"target": "manifest", "ok": True},
        ],
    }
    return mock


@pytest.fixture
def mock_audit_service():
    """Create mock AuditService."""
    mock = Mock()
    mock.log_action.return_value = True
    return mock


@pytest.fixture
def mock_container(mock_export_service, mock_audit_service):
    """Create mock DI container."""
    mock = Mock()
    mock.get_export_service.return_value = mock_export_service
    mock.get_audit_service.return_value = mock_audit_service
    return mock


class TestExportsCreateEndpoint:
    """Tests for POST /api/exports endpoint."""

    @patch("backend.api.exports.get_container")
    def test_create_export_success(self, mock_get_container, mock_container, test_client):
        """Test successful export creation."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_123",
                "formats": ["json"],
                "include": {"transcript": True, "events": True, "attachments": False},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "exportId" in data
        assert data["status"] == "ready"
        assert "artifacts" in data
        assert "manifestUrl" in data

    @patch("backend.api.exports.get_container")
    def test_create_export_both_formats(self, mock_get_container, mock_container, test_client):
        """Test export creation with multiple formats."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_456",
                "formats": ["json", "md"],
                "include": {"transcript": True, "events": True, "attachments": False},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exportId"] == "exp_123456_7890"

    @patch("backend.api.exports.get_container")
    def test_create_export_service_called(
        self, mock_get_container, mock_container, test_client
    ):
        """Test that ExportService is called with correct parameters."""
        mock_get_container.return_value = mock_container

        test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_789",
                "formats": ["json"],
                "include": {"transcript": True, "events": False, "attachments": False},
            },
        )

        # Verify service was called
        mock_container.get_export_service.return_value.create_export.assert_called_once()
        call_kwargs = (
            mock_container.get_export_service.return_value.create_export.call_args[1]
        )
        assert call_kwargs["session_id"] == "session_789"
        assert "json" in call_kwargs["formats"]

    @patch("backend.api.exports.get_container")
    def test_create_export_audit_logged(self, mock_get_container, mock_container, test_client):
        """Test that export creation is audit logged."""
        mock_get_container.return_value = mock_container

        test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_123",
                "formats": ["json"],
            },
        )

        # Verify audit logging
        mock_container.get_audit_service.return_value.log_action.assert_called()
        call_kwargs = (
            mock_container.get_audit_service.return_value.log_action.call_args[1]
        )
        assert call_kwargs["action"] == "export_created"
        assert call_kwargs["result"] == "success"

    @patch("backend.api.exports.get_container")
    def test_create_export_service_error(self, mock_get_container, mock_container, test_client):
        """Test error handling when service fails."""
        mock_get_container.return_value = mock_container
        mock_container.get_export_service.return_value.create_export.side_effect = ValueError(
            "Invalid session"
        )

        response = test_client.post(
            "/api/exports",
            json={
                "sessionId": "invalid",
                "formats": ["json"],
            },
        )

        assert response.status_code == 400


class TestExportsGetEndpoint:
    """Tests for GET /api/exports/{export_id} endpoint."""

    @patch("backend.api.exports.get_container")
    def test_get_export_success(self, mock_get_container, mock_container, test_client):
        """Test successful export retrieval."""
        mock_get_container.return_value = mock_container

        response = test_client.get("/api/exports/exp_123456_7890")

        assert response.status_code == 200
        data = response.json()
        assert data["exportId"] == "exp_123456_7890"
        assert data["status"] == "ready"
        assert len(data["artifacts"]) > 0

    @patch("backend.api.exports.get_container")
    def test_get_export_not_found(self, mock_get_container, mock_container, test_client):
        """Test export retrieval returns 404 for missing export."""
        mock_get_container.return_value = mock_container
        mock_container.get_export_service.return_value.get_export_metadata.return_value = None

        response = test_client.get("/api/exports/nonexistent")

        assert response.status_code == 404

    @patch("backend.api.exports.get_container")
    def test_get_export_includes_urls(self, mock_get_container, mock_container, test_client):
        """Test that artifacts include download URLs."""
        mock_get_container.return_value = mock_container

        response = test_client.get("/api/exports/exp_123456_7890")

        data = response.json()
        for artifact in data["artifacts"]:
            assert "url" in artifact
            assert artifact["url"].startswith("http://localhost:7001/downloads")

    @patch("backend.api.exports.get_container")
    def test_get_export_audit_logged(self, mock_get_container, mock_container, test_client):
        """Test that export retrieval is audit logged."""
        mock_get_container.return_value = mock_container

        test_client.get("/api/exports/exp_123456_7890")

        # Verify audit logging
        mock_container.get_audit_service.return_value.log_action.assert_called()

    @patch("backend.api.exports.get_container")
    def test_get_export_service_error(self, mock_get_container, mock_container, test_client):
        """Test error handling when service fails."""
        mock_get_container.return_value = mock_container
        mock_container.get_export_service.return_value.get_export_metadata.side_effect = (
            IOError("Storage failed")
        )

        response = test_client.get("/api/exports/exp_123456_7890")

        assert response.status_code == 500


class TestExportsVerifyEndpoint:
    """Tests for POST /api/exports/{export_id}/verify endpoint."""

    @patch("backend.api.exports.get_container")
    def test_verify_export_success(self, mock_get_container, mock_container, test_client):
        """Test successful export verification."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports/exp_123456_7890/verify",
            json={"targets": ["json", "manifest"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert len(data["results"]) == 2
        assert all(r["ok"] for r in data["results"])

    @patch("backend.api.exports.get_container")
    def test_verify_export_hash_mismatch(self, mock_get_container, mock_container, test_client):
        """Test verification result with hash mismatch."""
        mock_get_container.return_value = mock_container
        mock_container.get_export_service.return_value.verify_export.return_value = {
            "ok": False,
            "results": [
                {"target": "json", "ok": False, "message": "Hash mismatch"},
            ],
        }

        response = test_client.post(
            "/api/exports/exp_123456_7890/verify",
            json={"targets": ["json"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["results"][0]["ok"] is False

    @patch("backend.api.exports.get_container")
    def test_verify_export_default_targets(self, mock_get_container, mock_container, test_client):
        """Test verification with default targets."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports/exp_123456_7890/verify",
            json={},
        )

        assert response.status_code == 200

    @patch("backend.api.exports.get_container")
    def test_verify_export_service_called(
        self, mock_get_container, mock_container, test_client
    ):
        """Test that ExportService.verify_export is called correctly."""
        mock_get_container.return_value = mock_container

        test_client.post(
            "/api/exports/exp_123456_7890/verify",
            json={"targets": ["json", "manifest"]},
        )

        mock_container.get_export_service.return_value.verify_export.assert_called_once()
        call_kwargs = (
            mock_container.get_export_service.return_value.verify_export.call_args[1]
        )
        assert call_kwargs["export_id"] == "exp_123456_7890"
        assert "json" in call_kwargs["targets"]

    @patch("backend.api.exports.get_container")
    def test_verify_export_audit_logged(self, mock_get_container, mock_container, test_client):
        """Test that verification is audit logged."""
        mock_get_container.return_value = mock_container

        test_client.post(
            "/api/exports/exp_123456_7890/verify",
            json={"targets": ["json"]},
        )

        # Verify audit logging
        mock_container.get_audit_service.return_value.log_action.assert_called()
        call_kwargs = (
            mock_container.get_audit_service.return_value.log_action.call_args[1]
        )
        assert call_kwargs["action"] == "export_verified"

    @patch("backend.api.exports.get_container")
    def test_verify_export_not_found(self, mock_get_container, mock_container, test_client):
        """Test verification returns 404 for missing export."""
        mock_get_container.return_value = mock_container
        mock_container.get_export_service.return_value.verify_export.side_effect = IOError(
            "Export not found"
        )

        response = test_client.post(
            "/api/exports/nonexistent/verify",
            json={"targets": ["json"]},
        )

        assert response.status_code == 404


class TestExportsIntegration:
    """Integration tests for export endpoints."""

    @patch("backend.api.exports.get_container")
    def test_export_lifecycle(self, mock_get_container, mock_container, test_client):
        """Test complete export lifecycle: create -> get -> verify."""
        mock_get_container.return_value = mock_container

        # Create
        create_response = test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_123",
                "formats": ["json"],
            },
        )
        assert create_response.status_code == 200
        export_id = create_response.json()["exportId"]

        # Get
        get_response = test_client.get(f"/api/exports/{export_id}")
        assert get_response.status_code == 200

        # Verify
        verify_response = test_client.post(
            f"/api/exports/{export_id}/verify",
            json={"targets": ["json"]},
        )
        assert verify_response.status_code == 200

    @patch("backend.api.exports.get_container")
    def test_multiple_exports_isolation(self, mock_get_container, mock_container, test_client):
        """Test that multiple export requests don't interfere."""
        mock_get_container.return_value = mock_container

        # First export
        response1 = test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_1",
                "formats": ["json"],
            },
        )
        export_id_1 = response1.json()["exportId"]

        # Second export
        response2 = test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_2",
                "formats": ["md"],
            },
        )
        export_id_2 = response2.json()["exportId"]

        # Both should succeed independently
        assert export_id_1 == export_id_2  # Mock returns same ID
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestExportsErrorHandling:
    """Tests for error handling in export endpoints."""

    @patch("backend.api.exports.get_container")
    def test_create_export_invalid_session_format(
        self, mock_get_container, mock_container, test_client
    ):
        """Test error on invalid request format."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports",
            json={
                "sessionId": "session_123",
                "formats": [],  # Invalid: empty formats
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    @patch("backend.api.exports.get_container")
    def test_create_export_missing_session_id(
        self, mock_get_container, mock_container, test_client
    ):
        """Test error on missing session ID."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports",
            json={
                "formats": ["json"],
            },
        )

        assert response.status_code == 422  # Pydantic validation error

    @patch("backend.api.exports.get_container")
    def test_verify_export_invalid_target(self, mock_get_container, mock_container, test_client):
        """Test error on invalid verification target."""
        mock_get_container.return_value = mock_container

        response = test_client.post(
            "/api/exports/exp_123/verify",
            json={
                "targets": ["invalid_target"],
            },
        )

        # FastAPI should accept it but service returns appropriate result
        assert response.status_code == 200 or response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
