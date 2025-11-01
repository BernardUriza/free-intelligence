"""
Comprehensive mocked endpoint tests for diarization API.

Tests all 8 refactored diarization endpoints with mocked services:
- GET /api/diarization/jobs/{job_id}
- GET /api/diarization/result/{job_id}
- GET /api/diarization/export/{job_id}
- GET /api/diarization/jobs
- GET /api/diarization/health
- POST /api/diarization/jobs/{job_id}/restart
- POST /api/diarization/jobs/{job_id}/cancel
- GET /api/diarization/jobs/{job_id}/logs

Uses unittest.mock.Mock for service isolation and clean testing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.diarization import router


@pytest.fixture
def test_client():
    """Create a FastAPI app with diarization router for testing."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_container():
    """Create a mock DI container."""
    container = Mock()
    container.get_diarization_job_service = Mock()
    container.get_diarization_service = Mock()
    container.get_audit_service = Mock()
    return container


class TestGetJobStatus:
    """Test GET /api/diarization/jobs/{job_id}"""

    def test_get_job_status_success(self, test_client):
        """Test successful job status retrieval."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock service response
            mock_job_service.get_job_status.return_value = {
                "job_id": "job-123",
                "session_id": "session-456",
                "status": "processing",
                "progress_pct": 50,
                "total_chunks": 10,
                "processed_chunks": 5,
                "chunks": [
                    {
                        "chunk_idx": 0,
                        "start_time": 0.0,
                        "end_time": 5.0,
                        "text": "Hello world",
                        "speaker": "Speaker-1",
                        "temperature": 0.5,
                        "rtf": 0.25,
                        "timestamp": "2025-11-01T12:00:00Z",
                    }
                ],
                "created_at": "2025-11-01T12:00:00Z",
                "updated_at": "2025-11-01T12:05:00Z",
                "error": None,
            }

            # Make request
            response = test_client.get("/api/diarization/jobs/job-123")

            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job-123"
            assert data["status"] == "processing"
            assert data["progress_pct"] == 50
            assert len(data["chunks"]) == 1
            assert data["chunks"][0]["text"] == "Hello world"

            # Verify service was called
            mock_job_service.get_job_status.assert_called_once_with("job-123")
            mock_audit_service.log_action.assert_called_once()

    def test_get_job_status_not_found(self, test_client):
        """Test job status retrieval when job not found."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Job not found - service raises ValueError
            mock_job_service.get_job_status.side_effect = ValueError("Job not found")

            response = test_client.get("/api/diarization/jobs/nonexistent")

            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()


class TestGetDiarizationResult:
    """Test GET /api/diarization/result/{job_id}"""

    def test_get_result_success(self, test_client):
        """Test successful result retrieval."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock service response
            mock_job_service.get_diarization_result.return_value = {
                "session_id": "session-456",
                "audio_file_hash": "abc123def456",
                "duration_sec": 120.5,
                "language": "es",
                "model_asr": "faster-whisper",
                "model_llm": "none",
                "segments": [
                    {
                        "start_time": 0.0,
                        "end_time": 5.0,
                        "speaker": "Speaker-1",
                        "text": "Hola mundo",
                    },
                    {
                        "start_time": 5.0,
                        "end_time": 10.0,
                        "speaker": "Speaker-2",
                        "text": "Cómo estás",
                    },
                ],
                "processing_time_sec": 45.2,
                "created_at": "2025-11-01T12:00:00Z",
            }

            response = test_client.get("/api/diarization/result/job-123")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "session-456"
            assert data["duration_sec"] == 120.5
            assert len(data["segments"]) == 2
            assert data["segments"][0]["text"] == "Hola mundo"


class TestExportResult:
    """Test GET /api/diarization/export/{job_id}"""

    def test_export_json_success(self, test_client):
        """Test successful JSON export."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock JSON export response
            export_json = json.dumps({
                "job_id": "job-123",
                "session_id": "session-456",
                "segments": [
                    {"start_time": 0.0, "end_time": 5.0, "speaker": "Speaker-1", "text": "Hello"}
                ],
            })
            mock_job_service.export_result.return_value = export_json

            response = test_client.get("/api/diarization/export/job-123?format=json")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            assert "Content-Disposition" in response.headers
            data = json.loads(response.content)
            assert data["job_id"] == "job-123"

    def test_export_markdown_success(self, test_client):
        """Test successful markdown export."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock markdown export
            markdown_content = "# Diarization Result\n\n**[0.0s - 5.0s] Speaker-1:** Hello"
            mock_job_service.export_result.return_value = markdown_content

            response = test_client.get("/api/diarization/export/job-123?format=markdown")

            assert response.status_code == 200
            assert "text/markdown" in response.headers["content-type"]
            assert b"Diarization Result" in response.content

    def test_export_invalid_format(self, test_client):
        """Test export with invalid format."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Note: FastAPI regex validation happens before handler, so this should fail at validation
            response = test_client.get("/api/diarization/export/job-123?format=invalid")

            # The regex should reject the invalid format
            assert response.status_code == 422


class TestListDiarizationJobs:
    """Test GET /api/diarization/jobs"""

    def test_list_jobs_success(self, test_client):
        """Test successful job listing."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock job list
            mock_job_service.list_jobs.return_value = [
                {
                    "job_id": "job-1",
                    "session_id": "session-1",
                    "status": "completed",
                    "created_at": "2025-11-01T12:00:00Z",
                },
                {
                    "job_id": "job-2",
                    "session_id": "session-1",
                    "status": "processing",
                    "created_at": "2025-11-01T12:05:00Z",
                },
            ]

            response = test_client.get("/api/diarization/jobs?limit=50")

            assert response.status_code == 200
            data = response.json()
            # Response uses data field for list items
            assert "data" in data or "jobs" in data
            jobs = data.get("data", data.get("jobs", []))
            assert len(jobs) == 2
            assert jobs[0]["job_id"] == "job-1"

    def test_list_jobs_with_session_filter(self, test_client):
        """Test job listing with session filter."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock filtered job list
            mock_job_service.list_jobs.return_value = [
                {
                    "job_id": "job-1",
                    "session_id": "session-123",
                    "status": "completed",
                    "created_at": "2025-11-01T12:00:00Z",
                }
            ]

            response = test_client.get("/api/diarization/jobs?session_id=session-123&limit=50")

            assert response.status_code == 200
            mock_job_service.list_jobs.assert_called_once_with(limit=50, session_id="session-123")


class TestDiarizationHealth:
    """Test GET /api/diarization/health"""

    def test_health_check_healthy(self, test_client):
        """Test health check when service is healthy."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_diarization_service = Mock()
            mock_container.get_diarization_service.return_value = mock_diarization_service

            # Mock healthy response
            mock_diarization_service.health_check.return_value = {
                "service": "diarization",
                "status": "healthy",
                "components": {
                    "whisper": {"available": True, "model": "faster-whisper", "pytorch_available": True},
                    "ffmpeg": {"available": True, "version": "installed"},
                },
                "active_jobs": 2,
            }

            response = test_client.get("/api/diarization/health")

            assert response.status_code == 200
            data = json.loads(response.content)
            assert data["status"] == "healthy"
            assert data["components"]["whisper"]["available"] is True

    def test_health_check_degraded(self, test_client):
        """Test health check when service is degraded."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_diarization_service = Mock()
            mock_container.get_diarization_service.return_value = mock_diarization_service

            # Mock degraded response
            mock_diarization_service.health_check.return_value = {
                "service": "diarization",
                "status": "degraded",
                "components": {
                    "whisper": {"available": False, "reason": "faster-whisper not installed"},
                    "ffmpeg": {"available": True, "version": "installed"},
                },
                "active_jobs": 0,
            }

            response = test_client.get("/api/diarization/health")

            assert response.status_code == 503
            data = json.loads(response.content)
            assert data["status"] == "degraded"


class TestRestartJob:
    """Test POST /api/diarization/jobs/{job_id}/restart"""

    def test_restart_job_success(self, test_client):
        """Test successful job restart."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock restart response
            mock_job_service.restart_job.return_value = {
                "job_id": "job-new",
                "session_id": "session-456",
                "status": "pending",
            }

            response = test_client.post("/api/diarization/jobs/job-old/restart")

            assert response.status_code == 200
            data = response.json()
            # Response is a success_response with data field
            assert "data" in data or "message" in data
            assert "restarted" in str(data).lower()

    def test_restart_job_not_found(self, test_client):
        """Test restart when job not found."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock service raises ValueError
            mock_job_service.restart_job.side_effect = ValueError("Job not found")

            response = test_client.post("/api/diarization/jobs/nonexistent/restart")

            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()


class TestCancelJob:
    """Test POST /api/diarization/jobs/{job_id}/cancel"""

    def test_cancel_job_success(self, test_client):
        """Test successful job cancellation."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock cancel response
            mock_job_service.cancel_job.return_value = {
                "job_id": "job-123",
                "status": "cancelled",
            }

            response = test_client.post("/api/diarization/jobs/job-123/cancel")

            assert response.status_code == 200
            data = response.json()
            # Response is a success_response with data field
            assert "data" in data or "message" in data
            assert "cancelled" in str(data).lower()

    def test_cancel_job_validation_error(self, test_client):
        """Test cancel when job state doesn't allow cancellation."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock service raises ValueError (already completed)
            mock_job_service.cancel_job.side_effect = ValueError("Cannot cancel completed job")

            response = test_client.post("/api/diarization/jobs/job-123/cancel")

            assert response.status_code == 400
            assert "cannot" in response.json()["detail"].lower()


class TestGetJobLogs:
    """Test GET /api/diarization/jobs/{job_id}/logs"""

    def test_get_logs_success(self, test_client):
        """Test successful log retrieval."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock logs
            mock_job_service.get_job_logs.return_value = [
                {
                    "timestamp": "2025-11-01T12:00:00Z",
                    "level": "INFO",
                    "message": "Job started",
                },
                {
                    "timestamp": "2025-11-01T12:01:00Z",
                    "level": "INFO",
                    "message": "Processing chunk 1",
                },
            ]

            response = test_client.get("/api/diarization/jobs/job-123/logs")

            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 2
            assert data["data"][0]["message"] == "Job started"

    def test_get_logs_not_found(self, test_client):
        """Test log retrieval when job not found."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock service raises exception
            mock_job_service.get_job_logs.side_effect = ValueError("Job not found")

            response = test_client.get("/api/diarization/jobs/nonexistent/logs")

            assert response.status_code == 400
            assert "not found" in response.json()["detail"].lower()

    def test_get_logs_empty(self, test_client):
        """Test log retrieval when job has no logs."""
        with patch("backend.api.diarization.get_container") as mock_get_container:
            mock_container = Mock()
            mock_get_container.return_value = mock_container

            mock_job_service = Mock()
            mock_audit_service = Mock()
            mock_container.get_diarization_job_service.return_value = mock_job_service
            mock_container.get_audit_service.return_value = mock_audit_service

            # Mock empty logs
            mock_job_service.get_job_logs.return_value = []

            response = test_client.get("/api/diarization/jobs/job-123/logs")

            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 0
