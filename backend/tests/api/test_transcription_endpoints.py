"""Integration tests for transcription endpoints.

Tests the transcription API endpoints with improved validation and error handling.
"""

from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client for transcription API integration tests."""
    from backend.app.main import create_app

    app = create_app()
    return TestClient(app)


class TestTranscriptionEndpoints:
    """Integration tests for transcription API endpoints."""

    def test_stream_chunk_with_invalid_session_id(self, client):
        """Test POST /api/workflows/aurity/stream with invalid session ID."""
        audio_data = io.BytesIO(b"fake audio data")

        # Test with too short session ID
        response = client.post(
            "/api/workflows/aurity/stream",
            data={"session_id": "abc", "chunk_number": 0, "mode": "medical"},
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with too long session ID
        long_session_id = "a" * 200
        response = client.post(
            "/api/workflows/aurity/stream",
            data={"session_id": long_session_id, "chunk_number": 0, "mode": "medical"},
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid characters (URL encoded)
        response = client.post(
            "/api/workflows/aurity/stream",
            data={"session_id": "invalid%21%40%23session", "chunk_number": 0, "mode": "medical"},
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code in [400, 404]  # Either validation error or path not found

    def test_stream_chunk_with_invalid_chunk_number(self, client):
        """Test POST /api/workflows/aurity/stream with invalid chunk number."""
        audio_data = io.BytesIO(b"fake audio data")

        # Test with negative chunk number
        response = client.post(
            "/api/workflows/aurity/stream",
            data={"session_id": "valid_session_12345", "chunk_number": -1, "mode": "medical"},
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid chunk_number" in data["detail"]

        # Test with too large chunk number
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 20000,  # Exceeds 10000 limit
                "mode": "medical",
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid chunk_number" in data["detail"]

    def test_stream_chunk_with_invalid_mode(self, client):
        """Test POST /api/workflows/aurity/stream with invalid mode."""
        audio_data = io.BytesIO(b"fake audio data")

        # Test with invalid mode
        response = client.post(
            "/api/workflows/aurity/stream",
            data={"session_id": "valid_session_12345", "chunk_number": 0, "mode": "invalid_mode"},
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid mode" in data["detail"]

    def test_stream_chunk_with_invalid_audio_format(self, client):
        """Test POST /api/workflows/aurity/stream with invalid audio format."""
        fake_file_data = io.BytesIO(b"not actually an audio file")

        # Test with invalid audio format
        response = client.post(
            "/api/workflows/aurity/stream",
            data={"session_id": "valid_session_12345", "chunk_number": 0, "mode": "medical"},
            files={"audio": ("test.txt", fake_file_data, "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid audio format" in data["detail"]

    def test_stream_chunk_with_invalid_timestamps(self, client):
        """Test POST /api/workflows/aurity/stream with invalid timestamps."""
        audio_data = io.BytesIO(b"fake audio data")

        # Test with negative start timestamp
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "timestamp_start": -5.0,
                "timestamp_end": 10.0,
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid timestamp_start" in data["detail"]

        # Test with negative end timestamp
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "timestamp_start": 5.0,
                "timestamp_end": -10.0,
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid timestamp_end" in data["detail"]

        # Test with end timestamp before start timestamp
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "timestamp_start": 10.0,
                "timestamp_end": 5.0,  # End before start
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid timestamps" in data["detail"]

    def test_stream_chunk_with_invalid_patient_data(self, client):
        """Test POST /api/workflows/aurity/stream with invalid patient data."""
        audio_data = io.BytesIO(b"fake audio data")

        # Test with too short patient name
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "patient_name": "A",  # Only 1 character
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Patient name must be at least 2 characters" in data["detail"]

        # Test with invalid patient age
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "patient_age": "invalid_age",
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Patient age must be a number" in data["detail"]

        # Test with out of range patient age
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "patient_age": "200",  # Too old
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Patient age must be a number between 0 and 150" in data["detail"]

        # Test with too short chief complaint
        response = client.post(
            "/api/workflows/aurity/stream",
            data={
                "session_id": "valid_session_12345",
                "chunk_number": 0,
                "mode": "medical",
                "chief_complaint": "A",  # Only 1 character
            },
            files={"audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Chief complaint must be at least 3 characters" in data["detail"]

    def test_end_session_with_invalid_data(self, client):
        """Test POST /api/workflows/aurity/end-session with invalid data."""
        audio_data = io.BytesIO(b"fake audio data")

        # Test with invalid session ID
        response = client.post(
            "/api/workflows/aurity/end-session",
            data={"session_id": "invalid!@#session"},
            files={"full_audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid session_id format" in data["detail"]

        # Test with invalid audio format
        fake_file_data = io.BytesIO(b"not actually an audio file")
        response = client.post(
            "/api/workflows/aurity/end-session",
            data={"session_id": "valid_session_12345"},
            files={"full_audio": ("test.txt", fake_file_data, "text/plain")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid audio format" in data["detail"]

        # Test with invalid JSON for webspeech
        response = client.post(
            "/api/workflows/aurity/end-session",
            data={"session_id": "valid_session_12345", "webspeech_final": "invalid json {"},
            files={"full_audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid webspeech JSON" in data["detail"]

        # Test with non-array JSON for webspeech
        response = client.post(
            "/api/workflows/aurity/end-session",
            data={"session_id": "valid_session_12345", "webspeech_final": '{"not": "an array"}'},
            files={"full_audio": ("test.wav", audio_data, "audio/wav")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "Invalid webspeech format" in data["detail"]
