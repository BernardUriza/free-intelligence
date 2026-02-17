"""
Unit tests for session and task type models.
Tests Session, SessionStatus, EncryptionMetadata, TaskType, TaskStatus.

Coverage targets: backend/models/session.py, backend/models/task_type.py
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models.session import EncryptionMetadata, Session, SessionStatus
from backend.models.task_type import (
    CHUNK_DURATION_SECONDS,
    TaskStatus,
    TaskType,
)


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_active_status(self):
        """Should have ACTIVE status."""
        assert SessionStatus.ACTIVE.value == "active"

    def test_finalized_status(self):
        """Should have FINALIZED status."""
        assert SessionStatus.FINALIZED.value == "finalized"

    def test_diarized_status(self):
        """Should have DIARIZED status."""
        assert SessionStatus.DIARIZED.value == "diarized"

    def test_reviewed_status(self):
        """Should have REVIEWED status."""
        assert SessionStatus.REVIEWED.value == "reviewed"

    def test_completed_status(self):
        """Should have COMPLETED status."""
        assert SessionStatus.COMPLETED.value == "completed"

    def test_all_session_statuses(self):
        """Should have exactly 5 statuses."""
        statuses = list(SessionStatus)
        assert len(statuses) == 5

    def test_session_status_from_string(self):
        """Should create enum from string value."""
        status = SessionStatus("active")
        assert status == SessionStatus.ACTIVE


class TestEncryptionMetadata:
    """Tests for EncryptionMetadata class."""

    def test_encryption_metadata_defaults(self):
        """Should create with default values."""
        meta = EncryptionMetadata()
        
        assert meta.algorithm == "AES-GCM-256"
        assert meta.key_id == ""
        assert meta.iv == ""
        assert meta.encrypted_at == ""
        assert meta.encrypted_by == "system"

    def test_encryption_metadata_custom_values(self):
        """Should accept custom values."""
        meta = EncryptionMetadata(
            algorithm="AES-256-CBC",
            key_id="key-123",
            iv="iv-456",
            encrypted_at="2025-01-01T00:00:00Z",
            encrypted_by="admin",
        )
        
        assert meta.algorithm == "AES-256-CBC"
        assert meta.key_id == "key-123"
        assert meta.iv == "iv-456"
        assert meta.encrypted_at == "2025-01-01T00:00:00Z"
        assert meta.encrypted_by == "admin"

    def test_encryption_metadata_slots(self):
        """Should use __slots__ for memory efficiency."""
        assert hasattr(EncryptionMetadata, "__slots__")
        assert "algorithm" in EncryptionMetadata.__slots__
        assert "key_id" in EncryptionMetadata.__slots__


class TestSession:
    """Tests for Session class."""

    def test_session_creation_minimal(self):
        """Should create session with required fields."""
        session = Session(
            session_id="session-123",
            status=SessionStatus.ACTIVE,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        
        assert session.session_id == "session-123"
        assert session.status == SessionStatus.ACTIVE
        assert session.patient_id is None
        assert session.provider_id is None
        assert session.recording_duration == 0.0
        assert session.total_chunks == 0

    def test_session_creation_full(self):
        """Should create session with all fields."""
        encryption = EncryptionMetadata(key_id="key-123")
        session = Session(
            session_id="session-456",
            status=SessionStatus.FINALIZED,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T01:00:00Z",
            patient_id="patient-789",
            provider_id="provider-101",
            recording_duration=300.5,
            total_chunks=10,
            encryption_metadata=encryption,
            diarization_job_id="job-202",
            soap_note_path="/sessions/123/soap",
            finalized_at="2025-01-01T00:30:00Z",
            diarized_at="2025-01-01T00:45:00Z",
            reviewed_at="2025-01-01T00:50:00Z",
            completed_at="2025-01-01T01:00:00Z",
        )
        
        assert session.patient_id == "patient-789"
        assert session.provider_id == "provider-101"
        assert session.recording_duration == 300.5
        assert session.total_chunks == 10
        assert session.encryption_metadata == encryption

    def test_session_create_now(self):
        """Should create active session with current timestamp."""
        before = datetime.now(UTC)
        session = Session.create_now("new-session-id")
        after = datetime.now(UTC)
        
        assert session.session_id == "new-session-id"
        assert session.status == SessionStatus.ACTIVE
        assert session.created_at is not None
        # Verify timestamp is within expected range
        created = datetime.fromisoformat(session.created_at.replace("Z", "+00:00"))
        assert before <= created <= after

    def test_session_status_from_string(self):
        """Should convert string status to enum."""
        session = Session(
            session_id="test",
            status="active",  # String instead of enum
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        
        assert session.status == SessionStatus.ACTIVE

    def test_session_finalize(self):
        """Should mark session as finalized."""
        session = Session.create_now("finalize-test")
        encryption = EncryptionMetadata(key_id="key-xyz")
        
        session.finalize(encryption)
        
        assert session.status == SessionStatus.FINALIZED
        assert session.encryption_metadata == encryption
        assert session.finalized_at is not None
        assert session.updated_at == session.finalized_at

    def test_session_mark_diarized(self):
        """Should mark session as diarized."""
        session = Session.create_now("diarize-test")
        
        session.mark_diarized("job-123")
        
        assert session.status == SessionStatus.DIARIZED
        assert session.diarization_job_id == "job-123"
        assert session.diarized_at is not None

    def test_session_mark_reviewed(self):
        """Should mark session as reviewed."""
        session = Session.create_now("review-test")
        
        session.mark_reviewed()
        
        assert session.status == SessionStatus.REVIEWED
        assert session.reviewed_at is not None

    def test_session_mark_completed(self):
        """Should mark session as completed."""
        session = Session.create_now("complete-test")
        
        session.mark_completed("/path/to/soap")
        
        assert session.status == SessionStatus.COMPLETED
        assert session.soap_note_path == "/path/to/soap"
        assert session.completed_at is not None

    def test_session_to_dict(self):
        """Should serialize to dictionary."""
        session = Session.create_now("dict-test")
        session.patient_id = "patient-123"
        
        data = session.to_dict()
        
        assert data["session_id"] == "dict-test"
        assert data["status"] == "active"
        assert data["patient_id"] == "patient-123"
        assert data["encryption_metadata"] is None

    def test_session_to_dict_with_encryption(self):
        """Should serialize encryption metadata."""
        session = Session.create_now("encrypt-dict-test")
        session.finalize(EncryptionMetadata(key_id="key-abc", iv="iv-123"))
        
        data = session.to_dict()
        
        assert data["encryption_metadata"]["key_id"] == "key-abc"
        assert data["encryption_metadata"]["iv"] == "iv-123"
        assert data["encryption_metadata"]["algorithm"] == "AES-GCM-256"

    def test_session_from_dict(self):
        """Should deserialize from dictionary."""
        data = {
            "session_id": "from-dict-test",
            "status": "diarized",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T01:00:00Z",
            "patient_id": "patient-xyz",
            "provider_id": None,
            "recording_duration": 120.0,
            "total_chunks": 5,
            "encryption_metadata": None,
            "diarization_job_id": "job-abc",
            "soap_note_path": None,
            "finalized_at": None,
            "diarized_at": "2025-01-01T00:30:00Z",
            "reviewed_at": None,
            "completed_at": None,
        }
        
        session = Session.from_dict(data)
        
        assert session.session_id == "from-dict-test"
        assert session.status == SessionStatus.DIARIZED
        assert session.patient_id == "patient-xyz"
        assert session.recording_duration == 120.0

    def test_session_from_dict_with_encryption(self):
        """Should deserialize encryption metadata from dictionary."""
        data = {
            "session_id": "enc-dict-test",
            "status": "finalized",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "encryption_metadata": {
                "algorithm": "AES-GCM-256",
                "key_id": "key-restored",
                "iv": "iv-restored",
                "encrypted_at": "2025-01-01T00:00:00Z",
                "encrypted_by": "system",
            },
        }
        
        session = Session.from_dict(data)
        
        assert session.encryption_metadata is not None
        assert session.encryption_metadata.key_id == "key-restored"
        assert session.encryption_metadata.iv == "iv-restored"

    def test_session_slots(self):
        """Should use __slots__ for memory efficiency."""
        assert hasattr(Session, "__slots__")
        assert "session_id" in Session.__slots__
        assert "status" in Session.__slots__


class TestTaskType:
    """Tests for TaskType enum."""

    def test_transcription_task_type(self):
        """Should have TRANSCRIPTION type."""
        assert TaskType.TRANSCRIPTION.value == "TRANSCRIPTION"

    def test_diarization_task_type(self):
        """Should have DIARIZATION type."""
        assert TaskType.DIARIZATION.value == "DIARIZATION"

    def test_soap_generation_task_type(self):
        """Should have SOAP_GENERATION type."""
        assert TaskType.SOAP_GENERATION.value == "SOAP_GENERATION"

    def test_orders_task_type(self):
        """Should have ORDERS type."""
        assert TaskType.ORDERS.value == "ORDERS"

    def test_emotion_analysis_task_type(self):
        """Should have EMOTION_ANALYSIS type."""
        assert TaskType.EMOTION_ANALYSIS.value == "EMOTION_ANALYSIS"

    def test_encryption_task_type(self):
        """Should have ENCRYPTION type."""
        assert TaskType.ENCRYPTION.value == "ENCRYPTION"

    def test_summary_task_type(self):
        """Should have SUMMARY type."""
        assert TaskType.SUMMARY.value == "SUMMARY"

    def test_translation_task_type(self):
        """Should have TRANSLATION type."""
        assert TaskType.TRANSLATION.value == "TRANSLATION"

    def test_all_task_types(self):
        """Should have exactly 8 task types."""
        types = list(TaskType)
        assert len(types) == 8

    def test_task_type_is_str_enum(self):
        """TaskType should be a string enum."""
        assert isinstance(TaskType.TRANSCRIPTION, str)
        assert TaskType.TRANSCRIPTION == "TRANSCRIPTION"


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_pending_status(self):
        """Should have pending status."""
        assert TaskStatus.PENDING.value == "pending"

    def test_in_progress_status(self):
        """Should have in_progress status."""
        assert TaskStatus.IN_PROGRESS.value == "in_progress"

    def test_completed_status(self):
        """Should have completed status."""
        assert TaskStatus.COMPLETED.value == "completed"

    def test_failed_status(self):
        """Should have failed status."""
        assert TaskStatus.FAILED.value == "failed"

    def test_cancelled_status(self):
        """Should have cancelled status."""
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_all_task_statuses(self):
        """Should have exactly 5 statuses."""
        statuses = list(TaskStatus)
        assert len(statuses) == 5

    def test_task_status_is_str_enum(self):
        """TaskStatus should be a string enum."""
        assert isinstance(TaskStatus.PENDING, str)
        assert TaskStatus.PENDING == "pending"


class TestChunkDurationConstant:
    """Tests for CHUNK_DURATION_SECONDS constant."""

    def test_chunk_duration_is_positive(self):
        """Chunk duration should be positive."""
        assert CHUNK_DURATION_SECONDS > 0

    def test_chunk_duration_reasonable_range(self):
        """Chunk duration should be in reasonable range (5-60 seconds)."""
        assert 5 <= CHUNK_DURATION_SECONDS <= 60

    def test_chunk_duration_is_integer(self):
        """Chunk duration should be an integer."""
        assert isinstance(CHUNK_DURATION_SECONDS, int)
