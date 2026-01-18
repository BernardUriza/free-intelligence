"""Unit tests for backend/models.

Tests Pydantic models, enums, and data classes for:
- task_type.py: TaskType, TaskStatus enums
- job.py: JobType, JobStatus, Job class
- llm_model.py: LLMProvider, CostTier, LLMModel, LLMModelCreate, LLMModelUpdate

Coverage target: 90%+
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import ValidationError


# =============================================================================
# TaskType Tests
# =============================================================================
class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_types_exist(self) -> None:
        """All expected task types exist."""
        from backend.models.task_type import TaskType

        assert TaskType.TRANSCRIPTION.value == "TRANSCRIPTION"
        assert TaskType.DIARIZATION.value == "DIARIZATION"
        assert TaskType.SOAP_GENERATION.value == "SOAP_GENERATION"
        assert TaskType.ORDERS.value == "ORDERS"
        assert TaskType.EMOTION_ANALYSIS.value == "EMOTION_ANALYSIS"
        assert TaskType.ENCRYPTION.value == "ENCRYPTION"
        assert TaskType.SUMMARY.value == "SUMMARY"
        assert TaskType.TRANSLATION.value == "TRANSLATION"

    def test_task_type_count(self) -> None:
        """Verify expected number of task types."""
        from backend.models.task_type import TaskType

        assert len(TaskType) == 8

    def test_task_type_is_str_enum(self) -> None:
        """TaskType inherits from str for JSON serialization."""
        from backend.models.task_type import TaskType

        assert isinstance(TaskType.TRANSCRIPTION, str)
        assert TaskType.TRANSCRIPTION == "TRANSCRIPTION"


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_statuses_exist(self) -> None:
        """All expected task statuses exist."""
        from backend.models.task_type import TaskStatus

        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self) -> None:
        """Verify expected number of statuses."""
        from backend.models.task_type import TaskStatus

        assert len(TaskStatus) == 5

    def test_task_status_is_str_enum(self) -> None:
        """TaskStatus inherits from str for JSON serialization."""
        from backend.models.task_type import TaskStatus

        assert isinstance(TaskStatus.PENDING, str)
        assert TaskStatus.PENDING == "pending"


class TestChunkDuration:
    """Tests for CHUNK_DURATION_SECONDS constant."""

    def test_chunk_duration_exists(self) -> None:
        """CHUNK_DURATION_SECONDS is defined."""
        from backend.models.task_type import CHUNK_DURATION_SECONDS

        assert CHUNK_DURATION_SECONDS == 13
        assert isinstance(CHUNK_DURATION_SECONDS, int)


# =============================================================================
# JobType Tests
# =============================================================================
class TestJobType:
    """Tests for JobType enum."""

    def test_job_types_exist(self) -> None:
        """All expected job types exist."""
        from backend.models.job import JobType

        assert JobType.TRANSCRIPTION.value == "transcription"
        assert JobType.DIARIZATION.value == "diarization"
        assert JobType.SOAP_GENERATION.value == "soap_generation"
        assert JobType.EVIDENCE_EXTRACTION.value == "evidence_extraction"
        assert JobType.TIMELINE_VERIFICATION.value == "timeline_verification"

    def test_job_type_count(self) -> None:
        """Verify expected number of job types."""
        from backend.models.job import JobType

        assert len(JobType) == 5

    def test_job_type_is_str_enum(self) -> None:
        """JobType inherits from str."""
        from backend.models.job import JobType

        assert isinstance(JobType.TRANSCRIPTION, str)


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_job_statuses_exist(self) -> None:
        """All expected job statuses exist."""
        from backend.models.job import JobStatus

        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.IN_PROGRESS.value == "in_progress"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_job_status_count(self) -> None:
        """Verify expected number of statuses."""
        from backend.models.job import JobStatus

        assert len(JobStatus) == 5


# =============================================================================
# Job Class Tests
# =============================================================================
class TestJob:
    """Tests for Job class."""

    def test_job_creation_with_enums(self) -> None:
        """Job can be created with enum values."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job(
            job_id="job-123",
            session_id="session-456",
            job_type=JobType.TRANSCRIPTION,
            status=JobStatus.PENDING,
            created_at="2025-01-18T10:00:00Z",
        )
        assert job.job_id == "job-123"
        assert job.session_id == "session-456"
        assert job.job_type == JobType.TRANSCRIPTION
        assert job.status == JobStatus.PENDING
        assert job.progress_percent == 0
        assert job.depends_on == []
        assert job.result_data is None

    def test_job_creation_with_strings(self) -> None:
        """Job can be created with string values (converts to enums)."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job(
            job_id="job-123",
            session_id="session-456",
            job_type="transcription",
            status="pending",
            created_at="2025-01-18T10:00:00Z",
        )
        assert job.job_type == JobType.TRANSCRIPTION
        assert job.status == JobStatus.PENDING

    def test_job_create_now(self) -> None:
        """Job.create_now creates with current timestamp."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job.create_now(
            job_id="job-abc",
            session_id="session-xyz",
            job_type=JobType.DIARIZATION,
            depends_on=["job-123"],
        )
        assert job.status == JobStatus.PENDING
        assert job.depends_on == ["job-123"]
        assert job.created_at is not None
        assert job.updated_at == job.created_at

    def test_job_start(self) -> None:
        """Job.start() transitions to IN_PROGRESS."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job.create_now(
            job_id="job-1",
            session_id="sess-1",
            job_type=JobType.TRANSCRIPTION,
        )
        job.start()
        assert job.status == JobStatus.IN_PROGRESS
        assert job.started_at is not None
        assert job.updated_at == job.started_at

    def test_job_complete(self) -> None:
        """Job.complete() transitions to COMPLETED."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job.create_now(
            job_id="job-1",
            session_id="sess-1",
            job_type=JobType.TRANSCRIPTION,
        )
        job.start()
        job.complete(result_data={"chunks": 5})
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.progress_percent == 100
        assert job.result_data == {"chunks": 5}

    def test_job_complete_without_result(self) -> None:
        """Job.complete() works without result_data."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job.create_now(
            job_id="job-1",
            session_id="sess-1",
            job_type=JobType.TRANSCRIPTION,
        )
        job.complete()
        assert job.status == JobStatus.COMPLETED
        assert job.result_data is None

    def test_job_fail(self) -> None:
        """Job.fail() transitions to FAILED with error message."""
        from backend.models.job import Job, JobStatus, JobType

        job = Job.create_now(
            job_id="job-1",
            session_id="sess-1",
            job_type=JobType.TRANSCRIPTION,
        )
        job.start()
        job.fail("Connection timeout")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "Connection timeout"

    def test_job_update_progress(self) -> None:
        """Job.update_progress() clamps to 0-100."""
        from backend.models.job import Job, JobType

        job = Job.create_now(
            job_id="job-1",
            session_id="sess-1",
            job_type=JobType.TRANSCRIPTION,
        )
        job.update_progress(50)
        assert job.progress_percent == 50

        job.update_progress(150)  # Clamps to 100
        assert job.progress_percent == 100

        job.update_progress(-10)  # Clamps to 0
        assert job.progress_percent == 0

    def test_job_to_dict(self) -> None:
        """Job.to_dict() serializes correctly."""
        from backend.models.job import Job, JobType

        job = Job.create_now(
            job_id="job-1",
            session_id="sess-1",
            job_type=JobType.TRANSCRIPTION,
            depends_on=["job-0"],
        )
        data = job.to_dict()
        assert data["job_id"] == "job-1"
        assert data["session_id"] == "sess-1"
        assert data["job_type"] == "transcription"
        assert data["status"] == "pending"
        assert data["depends_on"] == ["job-0"]
        assert "created_at" in data

    def test_job_from_dict(self) -> None:
        """Job.from_dict() deserializes correctly."""
        from backend.models.job import Job, JobStatus, JobType

        data = {
            "job_id": "job-abc",
            "session_id": "sess-xyz",
            "job_type": "diarization",
            "status": "completed",
            "created_at": "2025-01-18T10:00:00Z",
            "completed_at": "2025-01-18T10:05:00Z",
            "progress_percent": 100,
        }
        job = Job.from_dict(data)
        assert job.job_id == "job-abc"
        assert job.job_type == JobType.DIARIZATION
        assert job.status == JobStatus.COMPLETED
        assert job.progress_percent == 100

    def test_job_from_dict_with_enums(self) -> None:
        """Job.from_dict() handles already-enum values."""
        from backend.models.job import Job, JobStatus, JobType

        data = {
            "job_id": "job-abc",
            "session_id": "sess-xyz",
            "job_type": JobType.DIARIZATION,
            "status": JobStatus.COMPLETED,
            "created_at": "2025-01-18T10:00:00Z",
        }
        job = Job.from_dict(data)
        assert job.job_type == JobType.DIARIZATION
        assert job.status == JobStatus.COMPLETED


# =============================================================================
# LLM Model Tests
# =============================================================================
class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_providers_exist(self) -> None:
        """All expected providers exist."""
        from backend.models.llm_model import LLMProvider

        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.AZURE.value == "azure"
        assert LLMProvider.OLLAMA.value == "ollama"

    def test_provider_count(self) -> None:
        """Verify expected number of providers."""
        from backend.models.llm_model import LLMProvider

        assert len(LLMProvider) == 4


class TestCostTier:
    """Tests for CostTier enum."""

    def test_cost_tiers_exist(self) -> None:
        """All expected cost tiers exist."""
        from backend.models.llm_model import CostTier

        assert CostTier.LOW.value == "low"
        assert CostTier.MEDIUM.value == "medium"
        assert CostTier.HIGH.value == "high"

    def test_cost_tier_count(self) -> None:
        """Verify expected number of tiers."""
        from backend.models.llm_model import CostTier

        assert len(CostTier) == 3


class TestLLMModel:
    """Tests for LLMModel Pydantic model."""

    def test_llm_model_creation(self) -> None:
        """LLMModel can be created with required fields."""
        from backend.models.llm_model import CostTier, LLMModel, LLMProvider

        model = LLMModel(
            id="gpt-4o",
            label="GPT-4o",
            provider=LLMProvider.OPENAI,
        )
        assert model.id == "gpt-4o"
        assert model.label == "GPT-4o"
        assert model.provider == "openai"  # use_enum_values=True
        assert model.cost_tier == "medium"
        assert model.max_tokens == 4096
        assert model.context_window == 128000
        assert model.is_active is True

    def test_llm_model_optional_fields(self) -> None:
        """LLMModel optional fields work correctly."""
        from backend.models.llm_model import LLMModel, LLMProvider

        model = LLMModel(
            id="llama-3",
            label="Llama 3",
            provider=LLMProvider.OLLAMA,
            description="Local Llama model",
            size_bytes=4_000_000_000,
            ram_required_gb=8.0,
        )
        assert model.description == "Local Llama model"
        assert model.size_bytes == 4_000_000_000
        assert model.ram_required_gb == 8.0


class TestLLMModelCreate:
    """Tests for LLMModelCreate Pydantic model."""

    def test_create_model_validation(self) -> None:
        """LLMModelCreate validates required fields."""
        from backend.models.llm_model import LLMModelCreate, LLMProvider

        model = LLMModelCreate(
            id="gpt-4o",
            label="GPT-4o",
            provider=LLMProvider.OPENAI,
        )
        assert model.id == "gpt-4o"

    def test_create_model_id_min_length(self) -> None:
        """LLMModelCreate enforces id min_length."""
        from backend.models.llm_model import LLMModelCreate, LLMProvider

        with pytest.raises(ValidationError) as exc_info:
            LLMModelCreate(
                id="a",  # Too short
                label="GPT-4o",
                provider=LLMProvider.OPENAI,
            )
        assert "String should have at least 2 characters" in str(exc_info.value)

    def test_create_model_id_max_length(self) -> None:
        """LLMModelCreate enforces id max_length."""
        from backend.models.llm_model import LLMModelCreate, LLMProvider

        with pytest.raises(ValidationError) as exc_info:
            LLMModelCreate(
                id="a" * 51,  # Too long
                label="GPT-4o",
                provider=LLMProvider.OPENAI,
            )
        assert "String should have at most 50 characters" in str(exc_info.value)

    def test_create_model_max_tokens_bounds(self) -> None:
        """LLMModelCreate enforces max_tokens bounds."""
        from backend.models.llm_model import LLMModelCreate, LLMProvider

        with pytest.raises(ValidationError) as exc_info:
            LLMModelCreate(
                id="gpt-4o",
                label="GPT-4o",
                provider=LLMProvider.OPENAI,
                max_tokens=0,  # Too low
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_create_model_context_window_bounds(self) -> None:
        """LLMModelCreate enforces context_window bounds."""
        from backend.models.llm_model import LLMModelCreate, LLMProvider

        with pytest.raises(ValidationError) as exc_info:
            LLMModelCreate(
                id="gpt-4o",
                label="GPT-4o",
                provider=LLMProvider.OPENAI,
                context_window=500,  # Too low (min 1024)
            )
        assert "greater than or equal to 1024" in str(exc_info.value)


class TestLLMModelUpdate:
    """Tests for LLMModelUpdate Pydantic model."""

    def test_update_model_all_optional(self) -> None:
        """LLMModelUpdate allows all fields to be optional."""
        from backend.models.llm_model import LLMModelUpdate

        model = LLMModelUpdate()
        assert model.label is None
        assert model.provider is None
        assert model.cost_tier is None

    def test_update_model_partial_update(self) -> None:
        """LLMModelUpdate allows partial updates."""
        from backend.models.llm_model import LLMModelUpdate

        model = LLMModelUpdate(label="New Label", is_active=False)
        assert model.label == "New Label"
        assert model.is_active is False
        assert model.provider is None


class TestLLMModelResponse:
    """Tests for LLMModelResponse Pydantic model."""

    def test_from_model_conversion(self) -> None:
        """LLMModelResponse.from_model() converts correctly."""
        from backend.models.llm_model import LLMModel, LLMModelResponse, LLMProvider

        model = LLMModel(
            id="gpt-4o",
            label="GPT-4o",
            provider=LLMProvider.OPENAI,
        )
        response = LLMModelResponse.from_model(model)
        assert response.id == "gpt-4o"
        assert response.label == "GPT-4o"
        assert response.provider == "openai"
        assert response.cost_tier == "medium"
        assert isinstance(response.created_at, str)
        assert isinstance(response.updated_at, str)


# =============================================================================
# Session Tests
# =============================================================================
class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_statuses_exist(self) -> None:
        """All expected session statuses exist."""
        from backend.models.session import SessionStatus

        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.FINALIZED.value == "finalized"
        assert SessionStatus.DIARIZED.value == "diarized"
        assert SessionStatus.REVIEWED.value == "reviewed"
        assert SessionStatus.COMPLETED.value == "completed"

    def test_status_count(self) -> None:
        """Verify expected number of statuses."""
        from backend.models.session import SessionStatus

        assert len(SessionStatus) == 5


class TestEncryptionMetadata:
    """Tests for EncryptionMetadata class."""

    def test_creation_defaults(self) -> None:
        """EncryptionMetadata has sensible defaults."""
        from backend.models.session import EncryptionMetadata

        meta = EncryptionMetadata()
        assert meta.algorithm == "AES-GCM-256"
        assert meta.encrypted_by == "system"
        assert meta.key_id == ""
        assert meta.iv == ""

    def test_creation_with_values(self) -> None:
        """EncryptionMetadata accepts all values."""
        from backend.models.session import EncryptionMetadata

        meta = EncryptionMetadata(
            algorithm="AES-CBC-256",
            key_id="key-123",
            iv="iv-abc",
            encrypted_at="2025-01-18T10:00:00Z",
            encrypted_by="admin",
        )
        assert meta.algorithm == "AES-CBC-256"
        assert meta.key_id == "key-123"
        assert meta.iv == "iv-abc"
        assert meta.encrypted_at == "2025-01-18T10:00:00Z"
        assert meta.encrypted_by == "admin"


class TestSession:
    """Tests for Session class."""

    def test_session_creation_with_enum(self) -> None:
        """Session can be created with enum status."""
        from backend.models.session import Session, SessionStatus

        session = Session(
            session_id="sess-123",
            status=SessionStatus.ACTIVE,
            created_at="2025-01-18T10:00:00Z",
            updated_at="2025-01-18T10:00:00Z",
        )
        assert session.session_id == "sess-123"
        assert session.status == SessionStatus.ACTIVE
        assert session.total_chunks == 0
        assert session.recording_duration == 0.0

    def test_session_creation_with_string(self) -> None:
        """Session can be created with string status."""
        from backend.models.session import Session, SessionStatus

        session = Session(
            session_id="sess-123",
            status="active",
            created_at="2025-01-18T10:00:00Z",
            updated_at="2025-01-18T10:00:00Z",
        )
        assert session.status == SessionStatus.ACTIVE

    def test_session_create_now(self) -> None:
        """Session.create_now creates active session."""
        from backend.models.session import Session, SessionStatus

        session = Session.create_now("sess-new")
        assert session.session_id == "sess-new"
        assert session.status == SessionStatus.ACTIVE
        assert session.created_at is not None

    def test_session_finalize(self) -> None:
        """Session.finalize() transitions to FINALIZED."""
        from backend.models.session import EncryptionMetadata, Session, SessionStatus

        session = Session.create_now("sess-1")
        meta = EncryptionMetadata(key_id="key-1", iv="iv-1")
        session.finalize(meta)

        assert session.status == SessionStatus.FINALIZED
        assert session.encryption_metadata == meta
        assert session.finalized_at is not None

    def test_session_mark_diarized(self) -> None:
        """Session.mark_diarized() transitions to DIARIZED."""
        from backend.models.session import Session, SessionStatus

        session = Session.create_now("sess-1")
        session.mark_diarized("diar-job-123")

        assert session.status == SessionStatus.DIARIZED
        assert session.diarization_job_id == "diar-job-123"
        assert session.diarized_at is not None

    def test_session_mark_reviewed(self) -> None:
        """Session.mark_reviewed() transitions to REVIEWED."""
        from backend.models.session import Session, SessionStatus

        session = Session.create_now("sess-1")
        session.mark_reviewed()

        assert session.status == SessionStatus.REVIEWED
        assert session.reviewed_at is not None

    def test_session_mark_completed(self) -> None:
        """Session.mark_completed() transitions to COMPLETED."""
        from backend.models.session import Session, SessionStatus

        session = Session.create_now("sess-1")
        session.mark_completed("/sessions/sess-1/soap/note.json")

        assert session.status == SessionStatus.COMPLETED
        assert session.soap_note_path == "/sessions/sess-1/soap/note.json"
        assert session.completed_at is not None

    def test_session_to_dict(self) -> None:
        """Session.to_dict() serializes correctly."""
        from backend.models.session import Session

        session = Session.create_now("sess-1")
        session.patient_id = "patient-abc"
        session.total_chunks = 5

        data = session.to_dict()
        assert data["session_id"] == "sess-1"
        assert data["status"] == "active"
        assert data["patient_id"] == "patient-abc"
        assert data["total_chunks"] == 5
        assert data["encryption_metadata"] is None

    def test_session_to_dict_with_encryption(self) -> None:
        """Session.to_dict() includes encryption metadata."""
        from backend.models.session import EncryptionMetadata, Session

        session = Session.create_now("sess-1")
        meta = EncryptionMetadata(key_id="key-1", iv="iv-1")
        session.finalize(meta)

        data = session.to_dict()
        assert data["encryption_metadata"]["algorithm"] == "AES-GCM-256"
        assert data["encryption_metadata"]["key_id"] == "key-1"

    def test_session_from_dict(self) -> None:
        """Session.from_dict() deserializes correctly."""
        from backend.models.session import Session, SessionStatus

        data = {
            "session_id": "sess-abc",
            "status": "finalized",
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:05:00Z",
            "total_chunks": 10,
        }
        session = Session.from_dict(data)
        assert session.session_id == "sess-abc"
        assert session.status == SessionStatus.FINALIZED
        assert session.total_chunks == 10

    def test_session_from_dict_with_encryption(self) -> None:
        """Session.from_dict() deserializes encryption metadata."""
        from backend.models.session import Session

        data = {
            "session_id": "sess-abc",
            "status": "finalized",
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:05:00Z",
            "encryption_metadata": {
                "algorithm": "AES-GCM-256",
                "key_id": "key-xyz",
                "iv": "iv-123",
                "encrypted_at": "2025-01-18T10:05:00Z",
                "encrypted_by": "system",
            },
        }
        session = Session.from_dict(data)
        assert session.encryption_metadata is not None
        assert session.encryption_metadata.key_id == "key-xyz"


# =============================================================================
# TranscriptionJob Tests
# =============================================================================
class TestChunkMetadata:
    """Tests for ChunkMetadata class."""

    def test_creation_required_fields(self) -> None:
        """ChunkMetadata requires chunk_number, status, audio_size_bytes."""
        from backend.models.transcription_job import ChunkMetadata

        chunk = ChunkMetadata(
            chunk_number=0,
            status="pending",
            audio_size_bytes=1024,
        )
        assert chunk.chunk_number == 0
        assert chunk.status == "pending"
        assert chunk.audio_size_bytes == 1024
        assert chunk.transcript is None

    def test_creation_all_fields(self) -> None:
        """ChunkMetadata accepts all optional fields."""
        from backend.models.transcription_job import ChunkMetadata

        chunk = ChunkMetadata(
            chunk_number=1,
            status="completed",
            audio_size_bytes=2048,
            audio_hash="abc123",
            transcript="Hello world",
            duration=13.5,
            language="es",
            confidence=0.95,
            audio_quality=0.88,
            timestamp_start=0.0,
            timestamp_end=13.5,
            created_at="2025-01-18T10:00:00Z",
        )
        assert chunk.transcript == "Hello world"
        assert chunk.confidence == 0.95
        assert chunk.language == "es"


class TestTranscriptionJob:
    """Tests for TranscriptionJob class."""

    def test_create_for_session(self) -> None:
        """TranscriptionJob.create_for_session creates correctly."""
        from backend.models.job import JobStatus, JobType
        from backend.models.transcription_job import TranscriptionJob

        job = TranscriptionJob.create_for_session(
            job_id="job-123",
            session_id="sess-456",
            total_chunks=5,
        )
        assert job.job_id == "job-123"
        assert job.session_id == "sess-456"
        assert job.job_type == JobType.TRANSCRIPTION
        assert job.status == JobStatus.PENDING
        assert job.total_chunks == 5
        assert job.processed_chunks == 0
        assert job.chunks == []

    def test_add_chunk_new(self) -> None:
        """TranscriptionJob.add_chunk adds new chunk."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1")
        chunk = ChunkMetadata(chunk_number=0, status="pending", audio_size_bytes=1024)
        job.add_chunk(chunk)

        assert len(job.chunks) == 1
        assert job.chunks[0].chunk_number == 0
        assert job.total_chunks == 1

    def test_add_chunk_updates_existing(self) -> None:
        """TranscriptionJob.add_chunk updates existing chunk."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1")
        chunk1 = ChunkMetadata(chunk_number=0, status="pending", audio_size_bytes=1024)
        job.add_chunk(chunk1)

        chunk2 = ChunkMetadata(chunk_number=0, status="completed", audio_size_bytes=1024)
        job.add_chunk(chunk2)

        assert len(job.chunks) == 1
        assert job.chunks[0].status == "completed"

    def test_add_chunks_sorted(self) -> None:
        """TranscriptionJob.add_chunk keeps chunks sorted."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1")
        job.add_chunk(ChunkMetadata(chunk_number=2, status="pending", audio_size_bytes=1024))
        job.add_chunk(ChunkMetadata(chunk_number=0, status="pending", audio_size_bytes=1024))
        job.add_chunk(ChunkMetadata(chunk_number=1, status="pending", audio_size_bytes=1024))

        assert [c.chunk_number for c in job.chunks] == [0, 1, 2]

    def test_mark_chunk_completed(self) -> None:
        """TranscriptionJob.mark_chunk_completed updates chunk."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1", total_chunks=2)
        job.add_chunk(ChunkMetadata(chunk_number=0, status="pending", audio_size_bytes=1024))
        job.add_chunk(ChunkMetadata(chunk_number=1, status="pending", audio_size_bytes=1024))

        job.mark_chunk_completed(
            chunk_number=0,
            transcript="Test transcript",
            duration=13.0,
            language="es",
            audio_hash="hash123",
            confidence=0.92,
            audio_quality=0.85,
            timestamp_start=0.0,
            timestamp_end=13.0,
            created_at="2025-01-18T10:00:00Z",
        )

        assert job.chunks[0].status == "completed"
        assert job.chunks[0].transcript == "Test transcript"
        assert job.processed_chunks == 1
        assert job.progress_percent == 50

    def test_mark_chunk_failed(self) -> None:
        """TranscriptionJob.mark_chunk_failed updates chunk."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1")
        job.add_chunk(ChunkMetadata(chunk_number=0, status="pending", audio_size_bytes=1024))

        job.mark_chunk_failed(0, "Whisper timeout")

        assert job.chunks[0].status == "failed"
        assert job.chunks[0].error_message == "Whisper timeout"

    def test_get_chunk(self) -> None:
        """TranscriptionJob.get_chunk returns chunk by number."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1")
        job.add_chunk(ChunkMetadata(chunk_number=0, status="pending", audio_size_bytes=1024))
        job.add_chunk(ChunkMetadata(chunk_number=1, status="pending", audio_size_bytes=2048))

        chunk = job.get_chunk(1)
        assert chunk is not None
        assert chunk.audio_size_bytes == 2048

        missing = job.get_chunk(99)
        assert missing is None

    def test_to_dict(self) -> None:
        """TranscriptionJob.to_dict serializes correctly."""
        from backend.models.transcription_job import ChunkMetadata, TranscriptionJob

        job = TranscriptionJob.create_for_session("job-1", "sess-1", total_chunks=1)
        job.add_chunk(ChunkMetadata(chunk_number=0, status="completed", audio_size_bytes=1024))
        job.primary_language = "en"

        data = job.to_dict()
        assert data["job_id"] == "job-1"
        assert data["job_type"] == "transcription"
        assert data["total_chunks"] == 1
        assert data["primary_language"] == "en"
        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["chunk_number"] == 0

    def test_from_dict(self) -> None:
        """TranscriptionJob.from_dict deserializes correctly."""
        from backend.models.job import JobStatus, JobType
        from backend.models.transcription_job import TranscriptionJob

        data = {
            "job_id": "job-abc",
            "session_id": "sess-xyz",
            "job_type": "transcription",
            "status": "in_progress",
            "created_at": "2025-01-18T10:00:00Z",
            "updated_at": "2025-01-18T10:05:00Z",
            "total_chunks": 3,
            "processed_chunks": 1,
            "primary_language": "es",
            "chunks": [
                {"chunk_number": 0, "status": "completed", "audio_size_bytes": 1024},
                {"chunk_number": 1, "status": "pending", "audio_size_bytes": 2048},
            ],
        }
        job = TranscriptionJob.from_dict(data)
        assert job.job_id == "job-abc"
        assert job.job_type == JobType.TRANSCRIPTION
        assert job.status == JobStatus.IN_PROGRESS
        assert job.total_chunks == 3
        assert len(job.chunks) == 2
        assert job.chunks[0].status == "completed"
