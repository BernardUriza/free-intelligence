"""Test cascade delete and referential integrity (Fix #5).

Tests for Session-Task relationship constraints:
- Cascade delete: Deleting session also deletes all associated tasks
- Referential integrity: Cannot create tasks for non-existent sessions

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import h5py
import pytest

from backend.domain.session import Session, SessionHDF5Metadata, SessionMapper
from backend.repositories.hdf5_session_repository import HDF5SessionRepository
from backend.repositories.task_repository import HDF5TaskRepository
from backend.utils.coder.utils.exceptions import SessionNotFoundError


class TestCascadeDeleteFix5:
    """Test suite for Fix #5 (cascade delete + referential integrity)."""

    @pytest.fixture
    def temp_h5_file(self) -> Path:
        """Create temporary HDF5 file for testing."""
        with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as temp:
            temp_path = Path(temp.name)
        # Initialize HDF5 structure
        with h5py.File(temp_path, "w") as f:
            f.create_group("sessions")
            f.create_group("tasks")
        return temp_path

    @pytest.fixture
    def task_repo(self, temp_h5_file: Path) -> HDF5TaskRepository:
        """Create HDF5TaskRepository instance (without session_repository yet)."""
        return HDF5TaskRepository(temp_h5_file)

    @pytest.fixture
    def session_repo(self, temp_h5_file: Path, task_repo: HDF5TaskRepository) -> HDF5SessionRepository:
        """Create HDF5SessionRepository instance with task_repository for cascade delete."""
        return HDF5SessionRepository(temp_h5_file, task_repository=task_repo)

    @pytest.fixture
    def task_repo_with_integrity(
        self, temp_h5_file: Path, session_repo: HDF5SessionRepository
    ) -> HDF5TaskRepository:
        """Create HDF5TaskRepository instance with session_repository for referential integrity."""
        return HDF5TaskRepository(temp_h5_file, session_repository=session_repo)

    @pytest.fixture
    def sample_session(self) -> Session:
        """Create sample session entity for testing."""
        from datetime import datetime, timezone
        from backend.domain.session import SessionStatus

        return Session(
            session_id="test-session-123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_active=datetime.now(timezone.utc),
            status=SessionStatus.ACTIVE,  # Use enum, not string
            interaction_count=5,
            is_persisted=True,
            owner_hash="owner-hash-456",
            thread_id="thread-789",
            has_transcription=False,
            has_diarization=False,
            has_soap=False,
            chunk_count=0,
            duration_seconds=0.0,
        )

    def test_cascade_delete_removes_all_tasks(
        self,
        session_repo: HDF5SessionRepository,
        task_repo: HDF5TaskRepository,
        sample_session: Session,
    ):
        """Test that deleting a session also deletes all associated tasks (CASCADE)."""
        # 1. Create session
        session_repo.save(sample_session)
        assert session_repo.exists(sample_session.session_id)

        # 2. Create multiple tasks for the session
        task_repo.ensure_task_exists(sample_session.session_id, "transcription", {"status": "started"})
        task_repo.ensure_task_exists(sample_session.session_id, "diarization", {"status": "started"})
        task_repo.ensure_task_exists(sample_session.session_id, "soap_generation", {"status": "pending"})

        # 3. Verify tasks exist
        assert task_repo.task_exists(sample_session.session_id, "transcription")
        assert task_repo.task_exists(sample_session.session_id, "diarization")
        assert task_repo.task_exists(sample_session.session_id, "soap_generation")

        # 4. DELETE SESSION (should cascade to tasks)
        deleted = session_repo.delete(sample_session.session_id)
        assert deleted is True

        # 5. CRITICAL ASSERTION: Tasks should be deleted too
        assert not task_repo.task_exists(sample_session.session_id, "transcription")
        assert not task_repo.task_exists(sample_session.session_id, "diarization")
        assert not task_repo.task_exists(sample_session.session_id, "soap_generation")

    def test_orphaned_task_creation_prevented(
        self,
        task_repo_with_integrity: HDF5TaskRepository,
        session_repo: HDF5SessionRepository,
    ):
        """Test that creating tasks for non-existent sessions raises SessionNotFoundError."""
        nonexistent_session_id = "nonexistent-session-999"

        # Verify session doesn't exist
        assert not session_repo.exists(nonexistent_session_id)

        # CRITICAL ASSERTION: Task creation should FAIL with SessionNotFoundError
        with pytest.raises(SessionNotFoundError) as exc_info:
            task_repo_with_integrity.ensure_task_exists(
                nonexistent_session_id, "transcription", {"status": "started"}
            )

        # Verify error message is descriptive
        assert "not found" in str(exc_info.value).lower()
        assert nonexistent_session_id in str(exc_info.value)

    def test_session_with_tasks_deletes_cleanly(
        self,
        session_repo: HDF5SessionRepository,
        task_repo: HDF5TaskRepository,
        sample_session: Session,
        temp_h5_file: Path,
    ):
        """Test that session deletion with tasks leaves clean HDF5 state (no orphans)."""
        # 1. Create session + tasks
        session_repo.save(sample_session)
        task_repo.ensure_task_exists(sample_session.session_id, "transcription")
        task_repo.ensure_task_exists(sample_session.session_id, "diarization")

        # 2. Delete session (cascade delete)
        session_repo.delete(sample_session.session_id)

        # 3. Verify HDF5 state is CLEAN (no orphaned data)
        with h5py.File(temp_h5_file, "r") as f:
            # Session group should not exist
            assert f"/sessions/{sample_session.session_id}" not in f

            # Tasks group for session should not exist
            assert f"/tasks/{sample_session.session_id}" not in f

    def test_delete_by_session_returns_count(
        self,
        task_repo: HDF5TaskRepository,
        session_repo: HDF5SessionRepository,
        sample_session: Session,
    ):
        """Test that delete_by_session() returns correct count of deleted task types."""
        # 1. Create session + tasks
        session_repo.save(sample_session)
        task_repo.ensure_task_exists(sample_session.session_id, "transcription")
        task_repo.ensure_task_exists(sample_session.session_id, "diarization")
        task_repo.ensure_task_exists(sample_session.session_id, "soap_generation")

        # 2. Delete tasks by session
        deleted_count = task_repo.delete_by_session(sample_session.session_id)

        # 3. CRITICAL ASSERTION: Should return 3 (3 task types deleted)
        assert deleted_count == 3

    def test_delete_by_session_idempotent(
        self,
        task_repo: HDF5TaskRepository,
        session_repo: HDF5SessionRepository,
        sample_session: Session,
    ):
        """Test that delete_by_session() is idempotent (safe to call twice)."""
        # 1. Create session (no tasks)
        session_repo.save(sample_session)

        # 2. Delete tasks (none exist)
        deleted_count_1 = task_repo.delete_by_session(sample_session.session_id)
        assert deleted_count_1 == 0

        # 3. Delete tasks again (should still be 0, no error)
        deleted_count_2 = task_repo.delete_by_session(sample_session.session_id)
        assert deleted_count_2 == 0

    def test_task_creation_allowed_with_existing_session(
        self,
        task_repo_with_integrity: HDF5TaskRepository,
        session_repo: HDF5SessionRepository,
        sample_session: Session,
    ):
        """Test that task creation works normally when session exists (positive case)."""
        # 1. Create session first
        session_repo.save(sample_session)

        # 2. Create task (should succeed because session exists)
        task_id = task_repo_with_integrity.ensure_task_exists(
            sample_session.session_id, "transcription", {"status": "started"}
        )

        # 3. Verify task was created
        assert task_id == f"{sample_session.session_id}/transcription"
        assert task_repo_with_integrity.task_exists(sample_session.session_id, "transcription")

    def test_backward_compat_without_cascade_delete(
        self,
        temp_h5_file: Path,
        sample_session: Session,
    ):
        """Test backward compatibility: session_repo without task_repository still works."""
        # Create repos WITHOUT dependency injection (old behavior)
        session_repo_no_cascade = HDF5SessionRepository(temp_h5_file)  # No task_repository
        task_repo_no_integrity = HDF5TaskRepository(temp_h5_file)  # No session_repository

        # 1. Create session + tasks
        session_repo_no_cascade.save(sample_session)
        task_repo_no_integrity.ensure_task_exists(sample_session.session_id, "transcription")

        # 2. Delete session (WITHOUT cascade)
        deleted = session_repo_no_cascade.delete(sample_session.session_id)
        assert deleted is True

        # 3. BACKWARD COMPAT: Tasks are NOT deleted (orphaned)
        # This is the OLD behavior - tasks remain after session deletion
        assert task_repo_no_integrity.task_exists(sample_session.session_id, "transcription")

        # This is acceptable for backward compat - new code will inject dependencies
