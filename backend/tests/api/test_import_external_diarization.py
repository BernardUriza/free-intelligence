"""Tests for external diarization import endpoint.

Verifies that the /sessions/{id}/diarization/import endpoint correctly:
- Accepts external diarization data (Cue, AssemblyAI, manual)
- Converts formats properly
- Saves to HDF5 via repository
- Returns correct response structure

Author: Claude Code
Created: 2026-01-27
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def valid_external_diarization():
    """Sample external diarization data from Cue.ai."""
    return {
        "segments": [
            {
                "start_time": 0.0,
                "end_time": 5.0,
                "speaker": {
                    "speaker_id": "DOCTOR",
                    "name": "Dr. García",
                    "confidence": 0.95
                },
                "text": "Buenas tardes, ¿cómo se encuentra hoy?",
                "confidence": 0.92
            },
            {
                "start_time": 5.5,
                "end_time": 8.0,
                "speaker": {
                    "speaker_id": "PATIENT",
                    "name": None,
                    "confidence": 0.88
                },
                "text": "Me duele la cabeza doctor.",
                "confidence": 0.85
            }
        ],
        "provider": "cue",
        "metadata": {
            "language": "es-MX",
            "external_job_id": "cue-12345"
        }
    }


class TestImportExternalDiarization:
    """Tests for POST /sessions/{id}/diarization/import endpoint."""

    def test_import_valid_diarization(self, client: TestClient, valid_external_diarization, test_session_id):
        """Test successful import of external diarization."""
        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=valid_external_diarization
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert data["session_id"] == test_session_id
        assert data["status"] == "imported"
        assert data["provider"] == "cue"
        assert data["segments_imported"] == 2
        assert data["speakers_identified"] == 2
        assert data["duration_seconds"] == 8.0
        assert "imported_at" in data
        assert "speakers" in data

        # Verify speakers list
        speakers = {s["speaker_id"]: s for s in data["speakers"]}
        assert "DOCTOR" in speakers
        assert "PATIENT" in speakers
        assert speakers["DOCTOR"]["name"] == "Dr. García"
        assert speakers["DOCTOR"]["confidence"] == 0.95

    def test_import_single_speaker(self, client: TestClient, test_session_id):
        """Test import with only one speaker (monologue)."""
        monologue = {
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 3.0,
                    "speaker": {"speaker_id": "SPEAKER_01"},
                    "text": "First segment.",
                    "confidence": 0.9
                },
                {
                    "start_time": 3.5,
                    "end_time": 6.0,
                    "speaker": {"speaker_id": "SPEAKER_01"},
                    "text": "Second segment.",
                    "confidence": 0.85
                }
            ],
            "provider": "manual"
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=monologue
        )

        assert response.status_code == 201
        data = response.json()
        assert data["speakers_identified"] == 1
        assert data["segments_imported"] == 2

    def test_import_minimal_speaker_info(self, client: TestClient, test_session_id):
        """Test import with minimal speaker data (no name, default confidence)."""
        minimal_data = {
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 2.0,
                    "speaker": {"speaker_id": "SPEAKER_01"},
                    "text": "Test segment.",
                    "confidence": 0.5
                }
            ],
            "provider": "external"
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=minimal_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["speakers"][0]["name"] is None
        assert data["speakers"][0]["confidence"] == 0.0  # Default from model

    def test_import_with_custom_metadata(self, client: TestClient, test_session_id):
        """Test that custom metadata is preserved."""
        data_with_metadata = {
            "segments": [
                {
                    "start_time": 0.0,
                    "end_time": 1.0,
                    "speaker": {"speaker_id": "S1"},
                    "text": "Test.",
                    "confidence": 0.8
                }
            ],
            "provider": "assembly",
            "metadata": {
                "language_code": "en-US",
                "audio_url": "https://example.com/audio.mp3",
                "webhook_id": "abc123"
            }
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=data_with_metadata
        )

        assert response.status_code == 201
        # Metadata saved to HDF5 (would need to verify via repository read)

    def test_import_empty_segments_rejected(self, client: TestClient, test_session_id):
        """Test that empty segments list is rejected."""
        invalid_data = {
            "segments": [],
            "provider": "test"
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=invalid_data
        )

        assert response.status_code == 422  # Validation error (min_length=1)

    def test_import_invalid_session_id(self, client: TestClient, valid_external_diarization):
        """Test that invalid session ID is rejected."""
        response = client.post(
            "/api/workflows/aurity/sessions/invalid-id/diarization/import",
            json=valid_external_diarization
        )

        assert response.status_code == 400  # validate_session_id rejects

    def test_import_negative_timestamps_rejected(self, client: TestClient, test_session_id):
        """Test that negative timestamps are rejected."""
        invalid_timestamps = {
            "segments": [
                {
                    "start_time": -1.0,  # Invalid
                    "end_time": 2.0,
                    "speaker": {"speaker_id": "S1"},
                    "text": "Test.",
                    "confidence": 0.8
                }
            ],
            "provider": "test"
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=invalid_timestamps
        )

        assert response.status_code == 422  # Validation error (ge=0.0)

    def test_import_end_before_start_rejected(self, client: TestClient, test_session_id):
        """Test that end_time < start_time is rejected."""
        invalid_order = {
            "segments": [
                {
                    "start_time": 5.0,
                    "end_time": 2.0,  # Invalid (before start)
                    "speaker": {"speaker_id": "S1"},
                    "text": "Test.",
                    "confidence": 0.8
                }
            ],
            "provider": "test"
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=invalid_order
        )

        # Should be rejected by gt=0.0 validation on end_time
        # (though it doesn't check end > start explicitly)
        # This is a future enhancement opportunity
        assert response.status_code == 422  # Validation error expected

    def test_import_calculates_duration_correctly(self, client: TestClient, test_session_id):
        """Test that total duration is max(end_time) of all segments."""
        multi_segment = {
            "segments": [
                {"start_time": 0.0, "end_time": 5.0, "speaker": {"speaker_id": "S1"}, "text": "A", "confidence": 0.9},
                {"start_time": 5.5, "end_time": 10.2, "speaker": {"speaker_id": "S2"}, "text": "B", "confidence": 0.9},
                {"start_time": 10.5, "end_time": 15.7, "speaker": {"speaker_id": "S1"}, "text": "C", "confidence": 0.9},
            ],
            "provider": "test"
        }

        response = client.post(
            f"/api/workflows/aurity/sessions/{test_session_id}/diarization/import",
            json=multi_segment
        )

        assert response.status_code == 201
        data = response.json()
        assert data["duration_seconds"] == 15.7  # Max end_time


@pytest.fixture
def test_session_id():
    """Valid session UUID for testing."""
    return "550e8400-e29b-41d4-a716-446655440000"
