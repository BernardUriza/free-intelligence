"""Endpoint tests for diarization API.

Tests the diarization endpoints with mocked services (clean code pattern).
Shows how to test FastAPI endpoints that use service layer with DI.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from backend.api.diarization import router
from fastapi import FastAPI


@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_diarization_service():
    """Mock DiarizationService."""
    mock = Mock()
    mock.create_diarization_job.return_value = {
        "job_id": "job_test_123",
        "session_id": "session_test_456",
        "filename": "test.mp3",
        "status": "pending",
        "language": "es",
        "created_at": "2025-11-01T12:00:00Z",
    }
    return mock


@pytest.fixture
def mock_audit_service():
    """Mock AuditService."""
    mock = Mock()
    mock.log_action.return_value = True
    return mock


@pytest.fixture
def mock_container():
    """Mock DI container."""
    mock = Mock()
    mock.get_diarization_service.return_value = Mock()
    mock.get_audit_service.return_value = Mock()
    return mock


class TestDiarizationEndpointUpload:
    """Tests for POST /upload endpoint."""

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_upload_success(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Test successful audio upload with service layer."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_save_audio.return_value = {
            "file_path": "audio/session_test/test_123.mp3",
            "session_id": "session_test_456",
        }

        # Create test audio file
        audio_content = b"fake audio data"

        # Make request
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={"language": "es", "persist": "false"},
            files={"audio": ("test.mp3", audio_content)},
        )

        # Verify response
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "success"
        assert data["code"] == 202
        assert data["data"]["job_id"] == "job_test_123"
        assert data["data"]["session_id"] == "session_test_456"

        # Verify service was called with correct parameters
        mock_diarization_service.create_diarization_job.assert_called_once()
        call_kwargs = mock_diarization_service.create_diarization_job.call_args[1]
        assert call_kwargs["session_id"] == "session_test_456"
        assert call_kwargs["audio_filename"] == "test.mp3"
        assert call_kwargs["language"] == "es"
        assert call_kwargs["persist"] is False

        # Verify audit logging was called
        mock_audit_service.log_action.assert_called()

    @patch("backend.api.diarization.get_container")
    def test_upload_validation_error(
        self,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Test upload with validation error from service."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Make service raise validation error
        mock_diarization_service.create_diarization_job.side_effect = ValueError(
            "File too large. Max: 100MB"
        )

        # Create test audio file
        audio_content = b"fake audio data"

        # Make request
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={"language": "es"},
            files={"audio": ("test.mp3", audio_content)},
        )

        # Verify error response
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "validation_error"
        assert "too large" in data["message"].lower()

        # Verify audit logged the failure
        assert mock_audit_service.log_action.called

    @patch("backend.api.diarization.get_container")
    def test_upload_storage_error(
        self,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Test upload with storage error."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Make service raise storage error
        mock_diarization_service.create_diarization_job.side_effect = IOError(
            "Failed to save audio file"
        )

        # Create test audio file
        audio_content = b"fake audio data"

        # Make request
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={"language": "es"},
            files={"audio": ("test.mp3", audio_content)},
        )

        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "internal_error"
        assert "storage" in data["message"].lower() or "audio" in data["message"].lower()

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_upload_missing_session_header(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Test upload without X-Session-ID header."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        # Make service raise validation error for missing session
        mock_diarization_service.create_diarization_job.side_effect = ValueError(
            "X-Session-ID header required"
        )

        # Create test audio file
        audio_content = b"fake audio data"

        # Make request WITHOUT session header
        response = test_client.post(
            "/api/diarization/upload",
            params={"language": "es"},
            files={"audio": ("test.mp3", audio_content)},
        )

        # Verify validation error
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "validation_error"

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_upload_with_config_overrides(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Test upload with optional config parameters."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_save_audio.return_value = {
            "file_path": "audio/session_test/test_123.mp3",
            "session_id": "session_test_456",
        }

        # Create test audio file
        audio_content = b"fake audio data"

        # Make request with optional parameters
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={
                "language": "es",
                "persist": "true",
                "whisper_model": "large-v3",
                "enable_llm_classification": "true",
                "chunk_size_sec": 30,
                "beam_size": 5,
                "vad_filter": "true",
            },
            files={"audio": ("test.mp3", audio_content)},
        )

        # Verify successful response
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "success"

        # Verify service was called with all parameters
        call_kwargs = mock_diarization_service.create_diarization_job.call_args[1]
        assert call_kwargs["language"] == "es"
        assert call_kwargs["persist"] is True
        assert call_kwargs["whisper_model"] == "large-v3"

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_upload_with_different_audio_formats(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Test upload with different audio file formats."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_save_audio.return_value = {
            "file_path": "audio/session_test/test_123.wav",
            "session_id": "session_test_456",
        }

        # Test different formats
        formats = ["mp3", "wav", "m4a", "ogg", "webm", "flac"]

        for fmt in formats:
            audio_content = b"fake audio data"

            response = test_client.post(
                "/api/diarization/upload",
                headers={"X-Session-ID": "session_test_456"},
                params={"language": "es"},
                files={"audio": (f"test.{fmt}", audio_content)},
            )

            # All should succeed
            assert response.status_code == 202, f"Failed for format {fmt}"
            data = response.json()
            assert data["status"] == "success"


class TestDiarizationEndpointIntegration:
    """Integration tests showing clean code architecture benefits."""

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_endpoint_delegates_to_service_layer(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Verify endpoint delegates validation to service (clean code)."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_save_audio.return_value = {
            "file_path": "audio/session_test/test_123.mp3",
            "session_id": "session_test_456",
        }

        # Make request
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={"language": "es"},
            files={"audio": ("test.mp3", b"fake audio data")},
        )

        # Endpoint should NOT do validation itself
        # Instead it should call service which does validation
        # This is verified by checking that create_diarization_job was called
        assert response.status_code == 202
        mock_diarization_service.create_diarization_job.assert_called_once()

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_endpoint_uses_di_container(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Verify endpoint uses DI container (no hardcoded dependencies)."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_save_audio.return_value = {
            "file_path": "audio/session_test/test_123.mp3",
            "session_id": "session_test_456",
        }

        # Make request
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={"language": "es"},
            files={"audio": ("test.mp3", b"fake audio data")},
        )

        # Verify container was called
        assert response.status_code == 202
        mock_get_container.assert_called()
        mock_container.get_diarization_service.assert_called()

    @patch("backend.api.diarization.get_container")
    @patch("backend.api.diarization.save_audio_file")
    def test_endpoint_logs_audit_trail(
        self,
        mock_save_audio,
        mock_get_container,
        test_client,
        mock_diarization_service,
        mock_audit_service,
    ):
        """Verify endpoint logs audit trail (compliance)."""
        # Setup mocks
        mock_container = Mock()
        mock_container.get_diarization_service.return_value = mock_diarization_service
        mock_container.get_audit_service.return_value = mock_audit_service
        mock_get_container.return_value = mock_container

        mock_save_audio.return_value = {
            "file_path": "audio/session_test/test_123.mp3",
            "session_id": "session_test_456",
        }

        # Make request
        response = test_client.post(
            "/api/diarization/upload",
            headers={"X-Session-ID": "session_test_456"},
            params={"language": "es"},
            files={"audio": ("test.mp3", b"fake audio data")},
        )

        # Verify audit logging
        assert response.status_code == 202
        mock_audit_service.log_action.assert_called()
        call_args = mock_audit_service.log_action.call_args_list
        assert len(call_args) >= 1
        assert "audio_uploaded_for_diarization" in str(call_args[0])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
