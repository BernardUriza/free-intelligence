"""
Test suite for Evidence API endpoints (backend/api/evidence.py)

Tests the clean code architecture pattern with service layer delegation,
DI container management, and audit logging.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.evidence import router
from backend.container import reset_container


@pytest.fixture(autouse=True)
def reset_di_container():
    """Reset DI container before and after each test."""
    reset_container()
    yield
    reset_container()


@pytest.fixture
def test_client():
    """Create FastAPI test client with evidence router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestCreateEvidencePack:
    """Tests for POST /api/evidence/packs endpoint."""

    def test_create_evidence_pack_success(self, test_client):
        """Test successful evidence pack creation."""
        payload = {
            "session_id": "session_20251101_120000",
            "sources": [
                {
                    "source_id": "src_001",
                    "tipo_doc": "lab_report",
                    "fecha": "2025-11-01",
                    "paciente_id": "pat_123",
                    "hallazgo": "Normal",
                    "severidad": "low",
                    "raw_text": "Lab results normal",
                }
            ],
        }

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert "pack_id" in data
        assert data["session_id"] == "session_20251101_120000"
        assert data["source_count"] == 1
        assert len(data["source_hashes"]) == 1
        assert "created_at" in data
        assert "policy_snapshot_id" in data
        assert "metadata" in data

    def test_create_evidence_pack_multiple_sources(self, test_client):
        """Test evidence pack creation with multiple sources."""
        payload = {
            "sources": [
                {
                    "source_id": "src_001",
                    "tipo_doc": "lab_report",
                    "fecha": "2025-11-01",
                    "paciente_id": "pat_123",
                }
            ]
            * 3,
        }

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["source_count"] == 3
        assert len(data["source_hashes"]) == 3

    def test_create_evidence_pack_no_session_id(self, test_client):
        """Test evidence pack creation without session_id."""
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

        assert response.status_code == 201
        data = response.json()
        assert data["session_id"] is None
        assert data["source_count"] == 1

    def test_create_evidence_pack_empty_sources(self, test_client):
        """Test evidence pack creation with empty sources list."""
        payload = {"sources": []}

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_create_evidence_pack_with_optional_fields(self, test_client):
        """Test evidence pack creation with all optional fields."""
        payload = {
            "session_id": "session_20251101_120000",
            "sources": [
                {
                    "source_id": "src_001",
                    "tipo_doc": "radiology",
                    "fecha": "2025-11-01",
                    "paciente_id": "pat_123",
                    "hallazgo": "Fracture detected",
                    "severidad": "high",
                    "raw_text": "X-ray shows fracture",
                }
            ],
        }

        response = test_client.post("/api/evidence/packs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["source_count"] == 1


class TestGetEvidencePack:
    """Tests for GET /api/evidence/packs/{pack_id} endpoint."""

    def test_get_evidence_pack_success(self, test_client):
        """Test successful evidence pack retrieval."""
        # Create a pack first
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
        create_response = test_client.post("/api/evidence/packs", json=payload)
        pack_id = create_response.json()["pack_id"]

        # Retrieve the pack
        response = test_client.get(f"/api/evidence/packs/{pack_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["pack_id"] == pack_id
        assert data["source_count"] == 1

    def test_get_evidence_pack_not_found(self, test_client):
        """Test evidence pack retrieval for non-existent pack."""
        response = test_client.get("/api/evidence/packs/pack_nonexistent")

        assert response.status_code == 404
        assert "detail" in response.json()


class TestGetSessionEvidence:
    """Tests for GET /api/evidence/sessions/{session_id}/evidence endpoint."""

    def test_get_session_evidence_success(self, test_client):
        """Test successful session evidence retrieval."""
        session_id = "session_20251101_120000"

        # Create multiple packs with same session
        for i in range(2):
            payload = {
                "session_id": session_id,
                "sources": [
                    {
                        "source_id": f"src_{i:03d}",
                        "tipo_doc": "lab_report",
                        "fecha": "2025-11-01",
                        "paciente_id": "pat_123",
                    }
                ],
            }
            test_client.post("/api/evidence/packs", json=payload)

        # Retrieve session evidence
        response = test_client.get(f"/api/evidence/sessions/{session_id}/evidence")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert all(pack["session_id"] == session_id for pack in data)

    def test_get_session_evidence_empty(self, test_client):
        """Test session evidence retrieval for session with no packs."""
        response = test_client.get("/api/evidence/sessions/session_empty/evidence")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_session_evidence_filters_by_session(self, test_client):
        """Test that session evidence filtering works correctly."""
        # Create packs with different sessions
        session1 = "session_001"
        session2 = "session_002"

        for session in [session1, session2]:
            payload = {
                "session_id": session,
                "sources": [
                    {
                        "source_id": "src_001",
                        "tipo_doc": "lab_report",
                        "fecha": "2025-11-01",
                        "paciente_id": "pat_123",
                    }
                ],
            }
            test_client.post("/api/evidence/packs", json=payload)

        # Retrieve session 1 evidence
        response = test_client.get(f"/api/evidence/sessions/{session1}/evidence")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["session_id"] == session1


class TestEvidenceIntegration:
    """Integration tests for evidence endpoints."""

    def test_create_retrieve_pack_workflow(self, test_client):
        """Test complete workflow: create and retrieve pack."""
        # Create pack
        payload = {
            "session_id": "session_20251101_120000",
            "sources": [
                {
                    "source_id": "src_001",
                    "tipo_doc": "lab_report",
                    "fecha": "2025-11-01",
                    "paciente_id": "pat_123",
                    "hallazgo": "Normal",
                }
            ],
        }
        create_response = test_client.post("/api/evidence/packs", json=payload)
        assert create_response.status_code == 201
        pack_id = create_response.json()["pack_id"]

        # Retrieve pack
        get_response = test_client.get(f"/api/evidence/packs/{pack_id}")
        assert get_response.status_code == 200

        # Get session evidence
        session_id = "session_20251101_120000"
        session_response = test_client.get(f"/api/evidence/sessions/{session_id}/evidence")
        assert session_response.status_code == 200
        assert len(session_response.json()) > 0

    def test_multiple_packs_same_session(self, test_client):
        """Test multiple packs in same session."""
        session_id = "session_20251101_120000"
        pack_ids = []

        # Create 3 packs
        for i in range(3):
            payload = {
                "session_id": session_id,
                "sources": [
                    {
                        "source_id": f"src_{i:03d}",
                        "tipo_doc": "lab_report",
                        "fecha": "2025-11-01",
                        "paciente_id": f"pat_{i:03d}",
                    }
                ],
            }
            response = test_client.post("/api/evidence/packs", json=payload)
            assert response.status_code == 201
            pack_ids.append(response.json()["pack_id"])

        # Verify all packs retrievable
        for pack_id in pack_ids:
            response = test_client.get(f"/api/evidence/packs/{pack_id}")
            assert response.status_code == 200

        # Verify session contains all packs
        session_response = test_client.get(f"/api/evidence/sessions/{session_id}/evidence")
        assert response.status_code == 200
        assert len(session_response.json()) == 3


class TestEvidenceErrorHandling:
    """Tests for error handling in evidence endpoints."""

    def test_invalid_json_payload(self, test_client):
        """Test handling of invalid JSON payload."""
        response = test_client.post("/api/evidence/packs", json={"invalid": "payload"})

        assert response.status_code == 422

    def test_missing_required_fields(self, test_client):
        """Test handling of missing required fields."""
        payload = {
            "session_id": "session_001",
            "sources": [
                {
                    # Missing required fields
                    "source_id": "src_001",
                }
            ],
        }

        response = test_client.post("/api/evidence/packs", json=payload)

        # Should fail validation
        assert response.status_code == 422
