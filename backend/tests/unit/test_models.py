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
