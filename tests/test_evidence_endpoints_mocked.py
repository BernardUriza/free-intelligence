"""
Test suite for Evidence API endpoints with mocked services

Uses mocked service layer to avoid pre-existing logging configuration issues.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.evidence import router


@pytest.fixture
def test_client():
    """Create FastAPI test client with evidence router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestCreateEvidencePackMocked:
    """Tests for POST /api/evidence/packs endpoint with mocked services."""

    @patch("backend.api.evidence.get_container")
    def test_create_evidence_pack_success(self, mock_get_container, test_client):
        """Test successful evidence pack creation."""
        # Mock services
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Mock service response
        mock_evidence_service.create_evidence_pack.return_value = {
            "pack_id": "pack_001",
            "created_at": "2025-11-01T12:00:00Z",
            "session_id": "session_001",
            "source_count": 1,
            "source_hashes": ["hash_001"],
            "policy_snapshot_id": "policy_001",
            "metadata": {},
        }

        payload = {
            "session_id": "session_001",
            "sources": [
                {
                    "source_id": "src_001",
                    "tipo_doc": "lab_report",
                    "fecha": "2025-11-01",
                    "paciente_id": "pat_123",
                }
            ],
        }

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["pack_id"] == "pack_001"
        assert data["source_count"] == 1
        mock_evidence_service.create_evidence_pack.assert_called_once()
        mock_audit_service.log_action.assert_called_once()

    @patch("backend.api.evidence.get_container")
    def test_create_evidence_pack_empty_sources(self, mock_get_container, test_client):
        """Test evidence pack creation with empty sources."""
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Mock service raises ValueError for empty sources
        mock_evidence_service.create_evidence_pack.side_effect = ValueError(
            "At least one source is required"
        )

        payload = {"sources": []}

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 400

    @patch("backend.api.evidence.get_container")
    def test_create_evidence_pack_service_error(self, mock_get_container, test_client):
        """Test evidence pack creation with service error."""
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Mock service error
        mock_evidence_service.create_evidence_pack.side_effect = Exception(
            "Storage error"
        )

        payload = {
            "sources": [
                {
                    "source_id": "src_001",
                    "tipo_doc": "lab_report",
                    "fecha": "2025-11-01",
                    "paciente_id": "pat_123",
                }
            ],
        }

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 500


class TestGetEvidencePackMocked:
    """Tests for GET /api/evidence/packs/{pack_id} endpoint."""

    @patch("backend.api.evidence.get_container")
    def test_get_evidence_pack_success(self, mock_get_container, test_client):
        """Test successful evidence pack retrieval."""
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_evidence_service.get_evidence_pack.return_value = {
            "pack_id": "pack_001",
            "created_at": "2025-11-01T12:00:00Z",
            "session_id": "session_001",
            "source_count": 1,
            "source_hashes": ["hash_001"],
            "policy_snapshot_id": "policy_001",
            "metadata": {},
        }

        response = test_client.get("/api/evidence/packs/pack_001")

        assert response.status_code == 200
        data = response.json()
        assert data["pack_id"] == "pack_001"

    @patch("backend.api.evidence.get_container")
    def test_get_evidence_pack_not_found(self, mock_get_container, test_client):
        """Test evidence pack retrieval for non-existent pack."""
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_evidence_service.get_evidence_pack.return_value = None

        response = test_client.get("/api/evidence/packs/nonexistent")

        assert response.status_code == 404


class TestGetSessionEvidenceMocked:
    """Tests for GET /api/evidence/sessions/{session_id}/evidence endpoint."""

    @patch("backend.api.evidence.get_container")
    def test_get_session_evidence_success(self, mock_get_container, test_client):
        """Test successful session evidence retrieval."""
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_evidence_service.get_session_evidence.return_value = [
            {
                "pack_id": "pack_001",
                "created_at": "2025-11-01T12:00:00Z",
                "session_id": "session_001",
                "source_count": 1,
                "source_hashes": ["hash_001"],
                "policy_snapshot_id": "policy_001",
                "metadata": {},
            }
        ]

        response = test_client.get("/api/evidence/sessions/session_001/evidence")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    @patch("backend.api.evidence.get_container")
    def test_get_session_evidence_empty(self, mock_get_container, test_client):
        """Test session evidence retrieval for session with no packs."""
        mock_evidence_service = Mock()
        mock_audit_service = Mock()
        mock_container = Mock()
        mock_container.get_evidence_service.return_value = mock_evidence_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_evidence_service.get_session_evidence.return_value = []

        response = test_client.get("/api/evidence/sessions/session_empty/evidence")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
