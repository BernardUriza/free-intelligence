"""
Unit tests for transcription_job model.
Tests TranscriptionJob class and edge cases.

Coverage targets: backend/models/transcription_job.py
"""

from __future__ import annotations

from backend.models.job import JobStatus, JobType
from backend.models.transcription_job import TranscriptionJob


class TestTranscriptionJob:
    """Tests for TranscriptionJob model."""

    def test_create_basic_transcription_job(self):
        """Should create basic transcription job."""
        job = TranscriptionJob.create_for_session(
            job_id="job-123",
            session_id="session-123",
            total_chunks=5,
        )
        
        assert job.session_id == "session-123"
        assert job.job_id == "job-123"
        assert job.total_chunks == 5
        assert job.job_type == JobType.TRANSCRIPTION

    def test_job_type_is_transcription(self):
        """Should have job_type set to TRANSCRIPTION."""
        from datetime import datetime, timezone
        
        job = TranscriptionJob(
            job_id="test-job-123",
            session_id="session-123",
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_chunks=3,
        )
        
        # Should be TRANSCRIPTION
        assert job.job_type == JobType.TRANSCRIPTION

    def test_transcription_job_chunks_default(self):
        """Should default chunks to empty list."""
        from datetime import datetime, timezone
        
        job = TranscriptionJob(
            job_id="test-job",
            session_id="session",
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_chunks=0,
        )
        
        assert job.chunks == []

    def test_transcription_job_with_chunks(self):
        """Should accept chunks."""
        from datetime import datetime, timezone
        
        chunks = [{"idx": 0, "transcript": "Hello"}]
        job = TranscriptionJob(
            job_id="test-job",
            session_id="session",
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_chunks=1,
            chunks=chunks,
        )
        
        assert len(job.chunks) == 1
        assert job.chunks[0]["transcript"] == "Hello"

    def test_transcription_job_audio_metadata(self):
        """Should store audio metadata."""
        from datetime import datetime, timezone
        
        job = TranscriptionJob(
            job_id="test-job",
            session_id="session",
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc).isoformat(),
            total_chunks=1,
            audio_file_path="/path/to/audio.webm",
            audio_duration=120.5,
            primary_language="es",
        )
        
        assert job.audio_file_path == "/path/to/audio.webm"
        assert job.audio_duration == 120.5
        assert job.primary_language == "es"
