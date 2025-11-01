"""
Test suite for Triage API endpoints (backend/api/triage.py)

Tests the clean code architecture pattern with service layer delegation,
DI container management, and audit logging.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.triage import router
from backend.container import reset_container


@pytest.fixture(autouse=True)
def reset_di_container():
    """Reset DI container before and after each test."""
    reset_container()
    yield
    reset_container()


@pytest.fixture
def test_client():
    """Create FastAPI test client with triage router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def sample_intake_payload():
    """Sample triage intake payload."""
    return {
        "reason": "Patient complaining of chest pain",
        "symptoms": ["chest pain", "shortness of breath"],
        "metadata": {"source": "mobile_app", "version": "1.0.0"},
    }


@pytest.fixture
def sample_intake_with_transcription():
    """Sample triage intake with audio transcription."""
    return {
        "reason": "Follow-up consultation",
        "symptoms": "fever,cough,fatigue",
        "audioTranscription": "Patient reports fever and cough for 3 days",
        "metadata": {"source": "web_portal"},
    }


class TestTriageIntake:
    """Tests for POST /api/triage/intake endpoint."""

    def test_intake_success(self, test_client, sample_intake_payload):
        """Test successful triage intake."""
        response = test_client.post("/api/triage/intake", json=sample_intake_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "bufferId" in data
        assert data["bufferId"].startswith("tri_")
        assert "receivedAt" in data
        assert "manifestUrl" in data

    def test_intake_with_transcription(self, test_client, sample_intake_with_transcription):
        """Test triage intake with audio transcription."""
        response = test_client.post("/api/triage/intake", json=sample_intake_with_transcription)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    def test_intake_symptoms_normalization(self, test_client):
        """Test symptoms string-to-list normalization."""
        payload = {
            "reason": "Test reason",
            "symptoms": "fever,cough,fatigue",  # String instead of list
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200

    def test_intake_symptoms_list(self, test_client):
        """Test intake with symptoms as list."""
        payload = {
            "reason": "Test reason",
            "symptoms": ["fever", "cough", "fatigue"],  # Already a list
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200

    def test_intake_with_metadata(self, test_client):
        """Test intake with custom metadata."""
        payload = {
            "reason": "Reason text",
            "symptoms": ["symptom1"],
            "metadata": {"custom_key": "custom_value", "nested": {"key": "value"}},
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200

    def test_intake_minimal_payload(self, test_client):
        """Test intake with minimal required fields."""
        payload = {"reason": "Patient complaint"}  # symptoms and others are optional

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "bufferId" in data

    def test_intake_reason_too_short(self, test_client):
        """Test intake with reason below minimum length."""
        payload = {"reason": "ab"}  # Less than 3 characters

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 422

    def test_intake_missing_reason(self, test_client):
        """Test intake without required reason field."""
        payload = {"symptoms": ["fever"]}

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 422

    def test_intake_transcription_too_long(self, test_client):
        """Test intake with transcription exceeding 32k chars."""
        long_text = "a" * 33_001
        payload = {
            "reason": "Reason",
            "audioTranscription": long_text,
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 422

    def test_intake_transcription_at_limit(self, test_client):
        """Test intake with transcription at 32k limit."""
        text_at_limit = "a" * 32_000
        payload = {
            "reason": "Reason",
            "audioTranscription": text_at_limit,
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200

    def test_intake_buffer_id_format(self, test_client, sample_intake_payload):
        """Test that buffer IDs follow expected format."""
        response = test_client.post("/api/triage/intake", json=sample_intake_payload)

        assert response.status_code == 200
        buffer_id = response.json()["bufferId"]
        assert buffer_id.startswith("tri_")
        assert len(buffer_id) == 36  # "tri_" + 32 hex chars


class TestTriageManifest:
    """Tests for GET /api/triage/manifest/{buffer_id} endpoint."""

    def test_get_manifest_success(self, test_client, sample_intake_payload):
        """Test successful manifest retrieval."""
        # Create buffer
        intake_response = test_client.post("/api/triage/intake", json=sample_intake_payload)
        buffer_id = intake_response.json()["bufferId"]
        manifest_url = intake_response.json()["manifestUrl"]

        # Retrieve manifest
        response = test_client.get(f"/api/triage/manifest/{buffer_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["bufferId"] == buffer_id
        assert "payloadHash" in data
        assert data["payloadHash"].startswith("sha256:")
        assert "receivedAt" in data
        assert "version" in data

    def test_manifest_contains_payload_subset(self, test_client, sample_intake_payload):
        """Test that manifest contains payload subset."""
        intake_response = test_client.post("/api/triage/intake", json=sample_intake_payload)
        buffer_id = intake_response.json()["bufferId"]

        response = test_client.get(f"/api/triage/manifest/{buffer_id}")

        assert response.status_code == 200
        data = response.json()
        assert "payloadSubset" in data
        assert "reason" in data["payloadSubset"]
        assert "symptomsCount" in data["payloadSubset"]
        assert "hasTranscription" in data["payloadSubset"]

    def test_manifest_not_found(self, test_client):
        """Test manifest retrieval for non-existent buffer."""
        response = test_client.get("/api/triage/manifest/tri_nonexistent")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_manifest_hash_consistency(self, test_client, sample_intake_payload):
        """Test that payload hash is consistent for same payload."""
        # Create two buffers with same payload
        response1 = test_client.post("/api/triage/intake", json=sample_intake_payload)
        response2 = test_client.post("/api/triage/intake", json=sample_intake_payload)

        buffer_id1 = response1.json()["bufferId"]
        buffer_id2 = response2.json()["bufferId"]

        # Get manifests
        manifest1 = test_client.get(f"/api/triage/manifest/{buffer_id1}").json()
        manifest2 = test_client.get(f"/api/triage/manifest/{buffer_id2}").json()

        # Hashes should match (same payload)
        assert manifest1["payloadHash"] == manifest2["payloadHash"]

    def test_manifest_hash_different_payload(self, test_client):
        """Test that different payloads produce different hashes."""
        payload1 = {
            "reason": "Reason 1",
            "symptoms": ["symptom1"],
        }
        payload2 = {
            "reason": "Reason 2",
            "symptoms": ["symptom2"],
        }

        response1 = test_client.post("/api/triage/intake", json=payload1)
        response2 = test_client.post("/api/triage/intake", json=payload2)

        buffer_id1 = response1.json()["bufferId"]
        buffer_id2 = response2.json()["bufferId"]

        manifest1 = test_client.get(f"/api/triage/manifest/{buffer_id1}").json()
        manifest2 = test_client.get(f"/api/triage/manifest/{buffer_id2}").json()

        # Hashes should be different
        assert manifest1["payloadHash"] != manifest2["payloadHash"]


class TestTriageIntegration:
    """Integration tests for triage endpoints."""

    def test_intake_to_manifest_workflow(self, test_client, sample_intake_payload):
        """Test complete workflow: intake then manifest retrieval."""
        # Step 1: Submit intake
        intake_response = test_client.post("/api/triage/intake", json=sample_intake_payload)
        assert intake_response.status_code == 200
        buffer_id = intake_response.json()["bufferId"]
        manifest_url = intake_response.json()["manifestUrl"]

        # Step 2: Retrieve manifest
        manifest_response = test_client.get(manifest_url)
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()
        assert manifest["bufferId"] == buffer_id

    def test_multiple_intakes_independent(self, test_client, sample_intake_payload):
        """Test that multiple intakes create independent buffers."""
        responses = []
        buffer_ids = []

        for _ in range(3):
            response = test_client.post("/api/triage/intake", json=sample_intake_payload)
            responses.append(response)
            buffer_ids.append(response.json()["bufferId"])

        # All should be unique
        assert len(set(buffer_ids)) == 3

        # All should be retrievable
        for buffer_id in buffer_ids:
            response = test_client.get(f"/api/triage/manifest/{buffer_id}")
            assert response.status_code == 200

    def test_intake_with_all_optional_fields(self, test_client):
        """Test intake with all optional fields filled."""
        payload = {
            "reason": "Complete patient intake",
            "symptoms": ["symptom1", "symptom2", "symptom3"],
            "audioTranscription": "Patient reports symptoms for 3 days",
            "metadata": {
                "source": "mobile_app",
                "version": "1.0.0",
                "timestamp": "2025-11-01T12:00:00Z",
                "custom": {"nested": "value"},
            },
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200
        buffer_id = response.json()["bufferId"]

        # Verify manifest contains all data
        manifest = test_client.get(f"/api/triage/manifest/{buffer_id}").json()
        assert manifest["payloadSubset"]["symptomsCount"] == 3
        assert manifest["payloadSubset"]["hasTranscription"] is True
        assert "metadata" in manifest


class TestTriageErrorHandling:
    """Tests for error handling in triage endpoints."""

    def test_invalid_json_payload(self, test_client):
        """Test handling of invalid JSON."""
        response = test_client.post("/api/triage/intake", json={"invalid": "payload"})

        assert response.status_code == 422

    def test_invalid_manifest_request(self, test_client):
        """Test invalid manifest request."""
        response = test_client.get("/api/triage/manifest/invalid_buffer_format")

        assert response.status_code == 404

    def test_intake_with_empty_symptoms_list(self, test_client):
        """Test intake with empty symptoms list."""
        payload = {
            "reason": "Patient complaint",
            "symptoms": [],
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200

    def test_intake_with_whitespace_only_symptoms(self, test_client):
        """Test intake with symptoms containing only whitespace."""
        payload = {
            "reason": "Patient complaint",
            "symptoms": "  ,  , ",  # Whitespace separated
        }

        response = test_client.post("/api/triage/intake", json=payload)

        assert response.status_code == 200
        # Should normalize to empty list or skip whitespace
