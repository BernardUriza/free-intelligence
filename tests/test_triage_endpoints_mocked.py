"""
Test suite for Triage API endpoints with mocked services

Uses mocked service layer for focused endpoint testing.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.triage import router


@pytest.fixture
def test_client():
    """Create FastAPI test client with triage router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestTriageIntakeMocked:
    """Tests for POST /api/triage/intake endpoint."""

    @patch("backend.api.triage.get_container")
    def test_intake_success(self, mock_get_container, test_client):
        """Test successful triage intake."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Mock service response
        mock_triage_service.create_buffer.return_value = {
            "buffer_id": "tri_abc123def456",
            "received_at": "2025-11-01T12:00:00Z",
            "manifest_url": "/api/triage/manifest/tri_abc123def456",
            "payload_hash": "sha256:abcd1234",
        }

        payload = {
            "reason": "Patient complaining of chest pain",
            "symptoms": ["chest pain", "shortness of breath"],
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["bufferId"] == "tri_abc123def456"
        assert "manifestUrl" in data
        mock_triage_service.create_buffer.assert_called_once()
        mock_audit_service.log_action.assert_called_once()

    @patch("backend.api.triage.get_container")
    def test_intake_with_transcription(self, mock_get_container, test_client):
        """Test triage intake with audio transcription."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_triage_service.create_buffer.return_value = {
            "buffer_id": "tri_xyz789def000",
            "received_at": "2025-11-01T12:00:00Z",
            "manifest_url": "/api/triage/manifest/tri_xyz789def000",
            "payload_hash": "sha256:xyz9876",
        }

        payload = {
            "reason": "Follow-up consultation",
            "symptoms": "fever,cough",
            "audioTranscription": "Patient reports fever",
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200

    @patch("backend.api.triage.get_container")
    def test_intake_reason_validation(self, mock_get_container, test_client):
        """Test intake with invalid reason."""
        payload = {"reason": "ab"}  # Too short

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 422

    @patch("backend.api.triage.get_container")
    def test_intake_transcription_length_validation(self, mock_get_container, test_client):
        """Test intake with transcription exceeding limit."""
        long_text = "a" * 33_001
        payload = {
            "reason": "Reason text",
            "audioTranscription": long_text,
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 422

    @patch("backend.api.triage.get_container")
    def test_intake_storage_error(self, mock_get_container, test_client):
        """Test intake with storage error."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_triage_service.create_buffer.side_effect = OSError("Disk full")

        payload = {
            "reason": "Patient complaint",
            "symptoms": ["fever"],
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 500


class TestTriageManifestMocked:
    """Tests for GET /api/triage/manifest/{buffer_id} endpoint."""

    @patch("backend.api.triage.get_container")
    def test_get_manifest_success(self, mock_get_container, test_client):
        """Test successful manifest retrieval."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_triage_service.get_manifest.return_value = {
            "version": "1.0.0",
            "bufferId": "tri_abc123def456",
            "receivedAt": "2025-11-01T12:00:00Z",
            "payloadHash": "sha256:abcd1234",
            "payloadSubset": {
                "reason": "Patient complaint",
                "symptomsCount": 2,
                "hasTranscription": False,
            },
            "metadata": {},
        }

        response = test_client.get("/api/triage/manifest/tri_abc123def456")

        assert response.status_code == 200
        data = response.json()
        assert data["bufferId"] == "tri_abc123def456"
        assert "payloadHash" in data
        mock_triage_service.get_manifest.assert_called_once()

    @patch("backend.api.triage.get_container")
    def test_manifest_with_transcription(self, mock_get_container, test_client):
        """Test manifest with transcription indicator."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_triage_service.get_manifest.return_value = {
            "version": "1.0.0",
            "bufferId": "tri_xyz789",
            "receivedAt": "2025-11-01T12:00:00Z",
            "payloadHash": "sha256:xyz9876",
            "payloadSubset": {
                "reason": "Follow-up",
                "symptomsCount": 3,
                "hasTranscription": True,
            },
            "metadata": {"source": "mobile_app"},
        }

        response = test_client.get("/api/triage/manifest/tri_xyz789")

        assert response.status_code == 200
        data = response.json()
        assert data["payloadSubset"]["hasTranscription"] is True

    @patch("backend.api.triage.get_container")
    def test_manifest_not_found(self, mock_get_container, test_client):
        """Test manifest retrieval for non-existent buffer."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_triage_service.get_manifest.return_value = None

        response = test_client.get("/api/triage/manifest/tri_nonexistent")

        assert response.status_code == 404


class TestTriageIntegrationMocked:
    """Integration tests for triage endpoints."""

    @patch("backend.api.triage.get_container")
    def test_intake_to_manifest_workflow(self, mock_get_container, test_client):
        """Test complete workflow: intake then manifest retrieval."""
        mock_triage_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_triage_service.return_value = mock_triage_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        buffer_id = "tri_abc123"
        manifest_url = f"/api/triage/manifest/{buffer_id}"

        # Setup for intake
        mock_triage_service.create_buffer.return_value = {
            "buffer_id": buffer_id,
            "received_at": "2025-11-01T12:00:00Z",
            "manifest_url": manifest_url,
            "payload_hash": "sha256:abcd1234",
        }

        # Setup for manifest retrieval
        mock_triage_service.get_manifest.return_value = {
            "version": "1.0.0",
            "bufferId": buffer_id,
            "receivedAt": "2025-11-01T12:00:00Z",
            "payloadHash": "sha256:abcd1234",
            "payloadSubset": {
                "reason": "Complaint",
                "symptomsCount": 2,
                "hasTranscription": False,
            },
            "metadata": {},
        }

        # Step 1: Intake
        payload = {
            "reason": "Patient complaint",
            "symptoms": ["symptom1", "symptom2"],
        }
        intake_response = test_client.post("/api/triage/intake", json=payload)
        assert intake_response.status_code == 200

        # Step 2: Get manifest
        manifest_response = test_client.get(manifest_url)
        assert manifest_response.status_code == 200
        assert manifest_response.json()["bufferId"] == buffer_id
