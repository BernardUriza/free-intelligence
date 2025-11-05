"""Unit tests for DiarizationService.

Tests the diarization service with mock dependencies.
Demonstrates the clean code testing pattern.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock

from backend.services.diarization_service import DiarizationService


@pytest.fixture
def mock_corpus_service():
    """Create mock CorpusService."""
    mock = Mock()
    mock.create_document.return_value = "doc_audio_123"
    return mock


@pytest.fixture
def mock_session_service():
    """Create mock SessionService."""
    mock = Mock()
    mock.get_session.return_value = {
        "session_id": "session_123",
        "status": "active",
        "user_id": "user_001"
    }
    return mock


@pytest.fixture
def diarization_service(mock_corpus_service, mock_session_service):
    """Create DiarizationService with mocked dependencies."""
    return DiarizationService(
        corpus_service=mock_corpus_service,
        session_service=mock_session_service
    )


class TestDiarizationServiceValidation:
    """Tests for audio file and session validation."""

    def test_validate_audio_file_success(self, diarization_service):
        """Test successful audio file validation."""
        is_valid, error = diarization_service.validate_audio_file(
            filename="test_audio.mp3",
            file_size=1024 * 100  # 100KB
        )

        assert is_valid is True
        assert error is None

    def test_validate_audio_file_missing_filename(self, diarization_service):
        """Test validation fails with missing filename."""
        is_valid, error = diarization_service.validate_audio_file(
            filename=None,
            file_size=1024
        )

        assert is_valid is False
        assert "Filename required" in error

    def test_validate_audio_file_no_extension(self, diarization_service):
        """Test validation fails with no file extension."""
        is_valid, error = diarization_service.validate_audio_file(
            filename="audio_file",  # No extension
            file_size=1024
        )

        assert is_valid is False
        assert "extension" in error.lower()

    def test_validate_audio_file_unsupported_extension(self, diarization_service):
        """Test validation fails with unsupported extension."""
        is_valid, error = diarization_service.validate_audio_file(
            filename="test.txt",  # Unsupported
            file_size=1024
        )

        assert is_valid is False
        assert "Unsupported" in error

    def test_validate_audio_file_too_large(self, diarization_service):
        """Test validation fails with oversized file."""
        is_valid, error = diarization_service.validate_audio_file(
            filename="test.mp3",
            file_size=200 * 1024 * 1024  # 200MB (exceeds 100MB limit)
        )

        assert is_valid is False
        assert "too large" in error.lower()

    def test_validate_audio_file_empty(self, diarization_service):
        """Test validation fails with empty file."""
        is_valid, error = diarization_service.validate_audio_file(
            filename="test.mp3",
            file_size=0
        )

        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_session_success(self, diarization_service):
        """Test successful session validation."""
        is_valid, error = diarization_service.validate_session("session_123")

        assert is_valid is True
        assert error is None

    def test_validate_session_missing(self, diarization_service):
        """Test validation fails with missing session."""
        is_valid, error = diarization_service.validate_session(None)

        assert is_valid is False
        assert "header required" in error.lower()

    def test_validate_session_not_found(self, diarization_service, mock_session_service):
        """Test validation fails when session not found."""
        mock_session_service.get_session.return_value = None

        is_valid, error = diarization_service.validate_session("invalid_session")

        assert is_valid is False
        assert "not found" in error.lower()

    def test_validate_session_deleted(self, diarization_service, mock_session_service):
        """Test validation fails when session is deleted."""
        mock_session_service.get_session.return_value = {
            "session_id": "session_123",
            "status": "deleted"
        }

        is_valid, error = diarization_service.validate_session("session_123")

        assert is_valid is False
        assert "deleted" in error.lower()


class TestDiarizationServiceJobCreation:
    """Tests for diarization job creation."""

    def test_create_diarization_job_success(self, diarization_service):
        """Test successful job creation."""
        result = diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"fake audio data",
            language="es"
        )

        assert result["job_id"] is not None
        assert result["session_id"] == "session_123"
        assert result["filename"] == "test.mp3"
        assert result["language"] == "es"
        assert result["status"] == "pending"

    def test_create_diarization_job_invalid_audio(self, diarization_service):
        """Test job creation fails with invalid audio."""
        with pytest.raises(ValueError, match="too large"):
            diarization_service.create_diarization_job(
                session_id="session_123",
                audio_filename="test.mp3",
                audio_content=b"x" * (200 * 1024 * 1024),  # Too large
                language="es"
            )

    def test_create_diarization_job_invalid_session(
        self, diarization_service, mock_session_service
    ):
        """Test job creation fails with invalid session."""
        mock_session_service.get_session.return_value = None

        with pytest.raises(ValueError, match="not found"):
            diarization_service.create_diarization_job(
                session_id="invalid",
                audio_filename="test.mp3",
                audio_content=b"audio",
                language="es"
            )

    def test_create_diarization_job_invalid_language(self, diarization_service):
        """Test job creation fails with invalid language."""
        with pytest.raises(ValueError, match="Language"):
            diarization_service.create_diarization_job(
                session_id="session_123",
                audio_filename="test.mp3",
                audio_content=b"audio",
                language=""  # Invalid
            )

    def test_create_diarization_job_storage_error(
        self, diarization_service, mock_corpus_service
    ):
        """Test job creation fails if storage fails."""
        mock_corpus_service.create_document.side_effect = IOError("Storage failed")

        with pytest.raises(IOError, match="Failed to save"):
            diarization_service.create_diarization_job(
                session_id="session_123",
                audio_filename="test.mp3",
                audio_content=b"audio",
                language="es"
            )


class TestDiarizationServiceJobTracking:
    """Tests for job tracking and status management."""

    def test_get_job_status_found(self, diarization_service):
        """Test retrieving job status."""
        # Create job first
        result = diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )
        job_id = result["job_id"]

        # Get status
        status = diarization_service.get_job_status(job_id)

        assert status is not None
        assert status["job_id"] == job_id
        assert status["status"] == "pending"

    def test_get_job_status_not_found(self, diarization_service):
        """Test retrieving non-existent job."""
        status = diarization_service.get_job_status("invalid_job_id")

        assert status is None

    def test_update_job_progress(self, diarization_service):
        """Test updating job progress."""
        # Create job first
        result = diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )
        job_id = result["job_id"]

        # Update progress
        success = diarization_service.update_job_progress(
            job_id=job_id,
            progress_pct=50,
            chunks_processed=5,
            total_chunks=10
        )

        assert success is True

        # Verify progress
        status = diarization_service.get_job_status(job_id)
        assert status["progress_pct"] == 50
        assert status["chunks_processed"] == 5

    def test_complete_job(self, diarization_service):
        """Test completing job."""
        # Create job first
        result = diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )
        job_id = result["job_id"]

        # Complete job
        success = diarization_service.complete_job(
            job_id=job_id,
            result={"chunks": [{"text": "Hello", "speaker": "A"}]}
        )

        assert success is True

        # Verify completion
        status = diarization_service.get_job_status(job_id)
        assert status["status"] == "completed"
        assert status["progress_pct"] == 100
        assert "result" in status

    def test_fail_job(self, diarization_service):
        """Test failing job."""
        # Create job first
        result = diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )
        job_id = result["job_id"]

        # Fail job
        success = diarization_service.fail_job(
            job_id=job_id,
            error="Processing failed"
        )

        assert success is True

        # Verify failure
        status = diarization_service.get_job_status(job_id)
        assert status["status"] == "failed"
        assert status["error"] == "Processing failed"


class TestDiarizationServiceJobListing:
    """Tests for job listing and filtering."""

    def test_list_all_jobs(self, diarization_service):
        """Test listing all jobs."""
        # Create multiple jobs
        for i in range(3):
            diarization_service.create_diarization_job(
                session_id=f"session_{i}",
                audio_filename="test.mp3",
                audio_content=b"audio",
                language="es"
            )

        jobs = diarization_service.list_jobs()

        assert len(jobs) == 3

    def test_list_jobs_by_session(self, diarization_service):
        """Test listing jobs filtered by session."""
        # Create jobs for different sessions
        diarization_service.create_diarization_job(
            session_id="session_A",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )
        diarization_service.create_diarization_job(
            session_id="session_B",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )

        # List jobs for session_A
        jobs = diarization_service.list_jobs(session_id="session_A")

        assert len(jobs) == 1
        assert jobs[0]["session_id"] == "session_A"

    def test_list_jobs_by_status(self, diarization_service):
        """Test listing jobs filtered by status."""
        # Create job
        result = diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )
        job_id = result["job_id"]

        # Complete one, leave one pending
        diarization_service.complete_job(job_id)

        # Create another (stays pending)
        diarization_service.create_diarization_job(
            session_id="session_123",
            audio_filename="test.mp3",
            audio_content=b"audio",
            language="es"
        )

        # List completed jobs
        completed = diarization_service.list_jobs(status="completed")

        assert len(completed) == 1
        assert completed[0]["status"] == "completed"

    def test_list_jobs_with_limit(self, diarization_service):
        """Test listing jobs with limit."""
        # Create multiple jobs
        for _ in range(5):
            diarization_service.create_diarization_job(
                session_id="session_123",
                audio_filename="test.mp3",
                audio_content=b"audio",
                language="es"
            )

        # List with limit
        jobs = diarization_service.list_jobs(limit=3)

        assert len(jobs) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
