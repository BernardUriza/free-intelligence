"""Extended unit tests for HDF5 tasks modules.

Additional tests for lifecycle, chunks, and task type operations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pathlib import Path

# ==============================================================================
# LIFECYCLE MODULE TESTS
# ==============================================================================


class TestTaskLifecycle:
    """Tests for task lifecycle operations."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    def test_ensure_task_exists_creates_new_task(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test ensure_task_exists creates new task."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            ensure_task_exists,
        )

        # Mock HDF5 file
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(side_effect=lambda x: False)
        mock_file.__getitem__ = MagicMock(return_value=MagicMock())
        mock_file.create_group = MagicMock(return_value=MagicMock())
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        path = ensure_task_exists("session-123", TaskType.TRANSCRIPTION)

        assert path == "/sessions/session-123/tasks/TRANSCRIPTION"

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    def test_ensure_task_exists_already_exists_allow_existing_true(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test ensure_task_exists with allow_existing=True when task exists."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            ensure_task_exists,
        )

        # Mock HDF5 file where task already exists
        mock_file = MagicMock()
        task_path = "/sessions/session-123/tasks/TRANSCRIPTION"
        mock_file.__contains__ = MagicMock(side_effect=lambda x: x == task_path)
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # allow_existing=True should return existing path without error
        path = ensure_task_exists("session-123", TaskType.TRANSCRIPTION, allow_existing=True)

        assert path == task_path

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    def test_ensure_task_exists_already_exists_allow_existing_false(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test ensure_task_exists with allow_existing=False when task exists."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            ensure_task_exists,
        )

        # Mock HDF5 file where task already exists
        mock_file = MagicMock()
        task_path = "/sessions/session-123/tasks/TRANSCRIPTION"
        mock_file.__contains__ = MagicMock(side_effect=lambda x: x == task_path)
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # allow_existing=False (default) should raise error
        with pytest.raises(ValueError, match="already exists"):
            ensure_task_exists("session-123", TaskType.TRANSCRIPTION, allow_existing=False)

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path")
    def test_task_exists_returns_false_no_file(
        self,
        mock_get_path: MagicMock,
    ) -> None:
        """Test task_exists returns False when file doesn't exist."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import task_exists

        mock_get_path.return_value = Path("/nonexistent/path.h5")

        result = task_exists("session-123", TaskType.TRANSCRIPTION)

        assert result is False

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path")
    def test_task_exists_returns_false_on_oserror(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test task_exists returns False when OSError occurs."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import task_exists

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Make locked_session_h5 raise OSError
        mock_locked.return_value.__enter__ = MagicMock(side_effect=OSError("Invalid HDF5"))
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = task_exists("session-123", TaskType.TRANSCRIPTION)

        assert result is False

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path")
    def test_list_session_tasks_returns_tasks(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test list_session_tasks returns task list."""
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            list_session_tasks,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Mock HDF5 file with tasks
        mock_tasks_group = MagicMock()
        mock_tasks_group.keys.return_value = ["TRANSCRIPTION", "DIARIZATION"]
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_tasks_group)
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = list_session_tasks("session-123")

        assert result == ["TRANSCRIPTION", "DIARIZATION"]

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path")
    def test_list_session_tasks_no_tasks_group(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test list_session_tasks returns empty when no tasks group."""
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            list_session_tasks,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Mock HDF5 file without tasks group
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)  # tasks_path not in f
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = list_session_tasks("session-123")

        assert result == []

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path")
    def test_list_session_tasks_on_exception(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test list_session_tasks returns empty on exception."""
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            list_session_tasks,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Make locked_session_h5 raise exception
        mock_locked.return_value.__enter__ = MagicMock(side_effect=Exception("HDF5 error"))
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = list_session_tasks("session-123")

        assert result == []

    def test_task_exists_with_string_task_type(self) -> None:
        """Test task_exists accepts string task type."""
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import task_exists

        result = task_exists("nonexistent-session", "TRANSCRIPTION")

        assert result is False

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path")
    def test_list_session_tasks_no_file(
        self,
        mock_get_path: MagicMock,
    ) -> None:
        """Test list_session_tasks returns empty when no file."""
        from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import (
            list_session_tasks,
        )

        mock_get_path.return_value = Path("/nonexistent/file.h5")

        result = list_session_tasks("session-123")

        assert result == []


# ==============================================================================
# TASK TYPE TESTS
# ==============================================================================


class TestTaskTypeIntegration:
    """Tests for TaskType enum integration with HDF5."""

    def test_task_type_to_string(self) -> None:
        """Test TaskType enum converts to string properly."""
        from backend.models.task_type import TaskType

        assert TaskType.TRANSCRIPTION.value == "TRANSCRIPTION"
        assert TaskType.DIARIZATION.value == "DIARIZATION"
        assert TaskType.SOAP_GENERATION.value == "SOAP_GENERATION"

    def test_task_status_values(self) -> None:
        """Test TaskStatus enum values."""
        from backend.models.task_type import TaskStatus

        # Lowercase values
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


# ==============================================================================
# CHUNK OPERATIONS TESTS
# ==============================================================================


class TestChunkOperations:
    """Tests for chunk-related operations."""

    def test_chunk_path_generation(self) -> None:
        """Test chunk path is generated correctly."""
        session_id = "session-123"
        task_type = "TRANSCRIPTION"
        chunk_idx = 5

        expected_path = f"/sessions/{session_id}/tasks/{task_type}/chunks/chunk_{chunk_idx}"

        assert expected_path == "/sessions/session-123/tasks/TRANSCRIPTION/chunks/chunk_5"

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_append_chunk_fails_when_task_not_exists(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test append_chunk_to_task fails when task doesn't exist."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            append_chunk_to_task,
        )

        mock_exists.return_value = False

        with pytest.raises(ValueError, match="does not exist"):
            append_chunk_to_task(
                session_id="session-123",
                task_type=TaskType.TRANSCRIPTION,
                chunk_idx=0,
                transcript="Hello",
                audio_hash="abc123",
                duration=1.0,
                language="en",
                timestamp_start=0.0,
                timestamp_end=1.0,
            )

    def test_count_task_chunks_import(self) -> None:
        """Test count_task_chunks can be imported."""
        from infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            count_task_chunks,
        )

        assert callable(count_task_chunks)

    def test_get_task_chunks_import(self) -> None:
        """Test get_task_chunks can be imported."""
        from infrastructure.storage.infrastructure.hdf5.tasks.chunks import get_task_chunks

        assert callable(get_task_chunks)


class TestGetTaskTranscript:
    """Tests for get_task_transcript function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.get_task_chunks")
    def test_get_task_transcript_empty_chunks(
        self,
        mock_get_chunks: MagicMock,
    ) -> None:
        """Test get_task_transcript returns empty string for no chunks."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            get_task_transcript,
        )

        mock_get_chunks.return_value = []

        result = get_task_transcript("session-123", TaskType.TRANSCRIPTION)

        assert result == ""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.get_task_chunks")
    def test_get_task_transcript_concatenates_chunks(
        self,
        mock_get_chunks: MagicMock,
    ) -> None:
        """Test get_task_transcript concatenates chunks."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            get_task_transcript,
        )

        mock_get_chunks.return_value = [
            {"transcript": "Hello"},
            {"transcript": "world"},
        ]

        result = get_task_transcript("session-123", TaskType.TRANSCRIPTION)

        assert "Hello" in result
        assert "world" in result


# ==============================================================================
# SOAP MODULE TESTS
# ==============================================================================


class TestSoapOperations:
    """Tests for SOAP operations."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.soap.locked_session_h5")
    def test_save_soap_data_path(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test save_soap_data returns correct path."""
        from infrastructure.storage.infrastructure.hdf5.tasks.soap import save_soap_data

        # Mock HDF5 file
        mock_file = MagicMock()
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)
        mock_task_group.create_dataset = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        soap_data = {"subjective": "Patient reports headache"}

        path = save_soap_data("session-123", soap_data)

        assert "SOAP_GENERATION" in path


# ==============================================================================
# MODULE EXPORTS TESTS
# ==============================================================================


class TestModuleExports:
    """Tests for module exports."""

    def test_tasks_package_exports(self) -> None:
        """Test tasks package exports expected functions."""
        from infrastructure.storage.infrastructure.hdf5 import tasks

        # Verify package can be imported
        assert tasks is not None

    def test_h5_file_access_exports(self) -> None:
        """Test h5_file_access exports open_h5_read."""
        from infrastructure.storage.infrastructure.hdf5.tasks import h5_file_access

        assert hasattr(h5_file_access, "open_h5_read")

    def test_lifecycle_exports(self) -> None:
        """Test lifecycle module exports expected functions."""
        from infrastructure.storage.infrastructure.hdf5.tasks import lifecycle

        assert hasattr(lifecycle, "ensure_task_exists")
        assert hasattr(lifecycle, "task_exists")
        assert hasattr(lifecycle, "list_session_tasks")

    def test_chunks_exports(self) -> None:
        """Test chunks module exports expected functions."""
        from infrastructure.storage.infrastructure.hdf5.tasks import chunks

        assert hasattr(chunks, "append_chunk_to_task")
        assert hasattr(chunks, "count_task_chunks")
        assert hasattr(chunks, "get_task_chunks")
        assert hasattr(chunks, "get_task_transcript")

    def test_soap_exports(self) -> None:
        """Test soap module exports expected functions."""
        from infrastructure.storage.infrastructure.hdf5.tasks import soap

        assert hasattr(soap, "save_soap_data")
        assert hasattr(soap, "get_soap_data")
