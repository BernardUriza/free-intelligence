"""Unit tests for HDF5 chunks module.

Tests cover chunk operations: append, count, get, update.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# APPEND CHUNK TESTS
# ==============================================================================


class TestAppendChunkToTask:
    """Tests for append_chunk_to_task function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_append_chunk_fails_when_task_not_exists(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test append_chunk_to_task raises when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
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

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_append_chunk_creates_chunk_group(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test append_chunk_to_task creates chunk group."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            append_chunk_to_task,
        )

        mock_exists.return_value = True

        # Mock HDF5 file
        mock_chunks_group = MagicMock()
        mock_chunks_group.__contains__ = MagicMock(return_value=False)  # chunk doesn't exist
        mock_chunks_group.create_group = MagicMock(return_value=MagicMock())

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)  # no chunks group
        mock_task_group.__getitem__ = MagicMock(return_value=mock_chunks_group)
        mock_task_group.create_group = MagicMock(return_value=mock_chunks_group)

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        path = append_chunk_to_task(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
            transcript="Hello world",
            audio_hash="abc123def456",
            duration=2.5,
            language="es",
            timestamp_start=0.0,
            timestamp_end=2.5,
        )

        assert path == "/sessions/session-123/tasks/TRANSCRIPTION/chunks/chunk_0"

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_append_chunk_raises_if_chunk_exists(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test append_chunk_to_task raises when chunk already exists."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            append_chunk_to_task,
        )

        mock_exists.return_value = True

        # Mock HDF5 file where chunk already exists
        mock_chunks_group = MagicMock()
        mock_chunks_group.__contains__ = MagicMock(return_value=True)  # chunk exists

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)  # chunks group exists
        mock_task_group.__getitem__ = MagicMock(return_value=mock_chunks_group)

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="already exists"):
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

    def test_append_chunk_with_string_task_type(self) -> None:
        """Test append_chunk_to_task accepts string task type."""
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            append_chunk_to_task,
        )

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists"
        ) as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(ValueError, match="does not exist"):
                append_chunk_to_task(
                    session_id="session-123",
                    task_type="TRANSCRIPTION",  # string instead of enum
                    chunk_idx=0,
                    transcript="Hello",
                    audio_hash="abc123",
                    duration=1.0,
                    language="en",
                    timestamp_start=0.0,
                    timestamp_end=1.0,
                )


# ==============================================================================
# COUNT CHUNKS TESTS
# ==============================================================================


class TestCountTaskChunks:
    """Tests for count_task_chunks function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_count_chunks_returns_zero_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test count_task_chunks returns (0, 0) when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            count_task_chunks,
        )

        mock_exists.return_value = False

        result = count_task_chunks("session-123", TaskType.TRANSCRIPTION)

        assert result == (0, 0)

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.get_task_metadata")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_count_chunks_returns_metadata_total(
        self,
        mock_exists: MagicMock,
        mock_metadata: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test count_task_chunks returns expected total from metadata."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            count_task_chunks,
        )

        mock_exists.return_value = True
        mock_metadata.return_value = {"total_chunks": 5}

        # Mock HDF5 file with no chunks yet
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)
        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = count_task_chunks("session-123", TaskType.TRANSCRIPTION)

        assert result == (5, 0)

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.get_task_metadata")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_count_chunks_counts_actual_chunks(
        self,
        mock_exists: MagicMock,
        mock_metadata: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test count_task_chunks counts actual chunks in HDF5."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            count_task_chunks,
        )

        mock_exists.return_value = True
        mock_metadata.return_value = {"total_chunks": 5}

        # Mock chunk with transcript
        mock_chunk = MagicMock()
        mock_chunk.__contains__ = MagicMock(return_value=True)
        mock_chunk.__getitem__ = MagicMock(return_value=MagicMock(__call__=lambda: b"text"))

        # Mock chunks group with 3 chunks
        mock_chunks_group = MagicMock()
        mock_chunks_group.__iter__ = MagicMock(
            return_value=iter(["chunk_0", "chunk_1", "chunk_2"])
        )
        mock_chunks_group.__getitem__ = MagicMock(return_value=mock_chunk)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_chunks_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = count_task_chunks("session-123", TaskType.TRANSCRIPTION)

        # Expected 5, actual 3
        assert result[0] == 5


# ==============================================================================
# GET CHUNKS TESTS
# ==============================================================================


class TestGetTaskChunks:
    """Tests for get_task_chunks function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_get_chunks_returns_empty_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test get_task_chunks returns empty list when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            get_task_chunks,
        )

        mock_exists.return_value = False

        result = get_task_chunks("session-123", TaskType.TRANSCRIPTION)

        assert result == []


# ==============================================================================
# GET TRANSCRIPT TESTS
# ==============================================================================


class TestGetTaskTranscript:
    """Tests for get_task_transcript function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_get_transcript_returns_empty_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test get_task_transcript returns empty string when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            get_task_transcript,
        )

        mock_exists.return_value = False

        result = get_task_transcript("session-123", TaskType.TRANSCRIPTION)

        assert result == ""


# ==============================================================================
# CREATE EMPTY CHUNK TESTS
# ==============================================================================


class TestCreateEmptyChunk:
    """Tests for create_empty_chunk function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_create_empty_chunk_fails_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test create_empty_chunk raises when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            create_empty_chunk,
        )

        mock_exists.return_value = False

        with pytest.raises(ValueError, match="does not exist"):
            create_empty_chunk(
                session_id="session-123",
                task_type=TaskType.TRANSCRIPTION,
                chunk_idx=0,
            )


# ==============================================================================
# UPDATE CHUNK TESTS
# ==============================================================================


class TestUpdateChunkDataset:
    """Tests for update_chunk_dataset function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_update_chunk_fails_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test update_chunk_dataset returns False when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            update_chunk_dataset,
        )

        mock_exists.return_value = False

        result = update_chunk_dataset(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
            field="transcript",
            value="Updated text",
        )

        assert result is False

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_update_chunk_returns_false_when_chunk_not_found(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
        mock_h5_lock: MagicMock,
    ) -> None:
        """Test update_chunk_dataset returns False when chunk doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            update_chunk_dataset,
        )

        mock_exists.return_value = True

        # Mock HDF5 file where chunk doesn't exist
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = update_chunk_dataset(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
            field="transcript",
            value="Updated text",
        )

        assert result is False


# ==============================================================================
# BATCH UPDATE TESTS
# ==============================================================================


class TestBatchUpdateChunkDatasets:
    """Tests for batch_update_chunk_datasets function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_batch_update_fails_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test batch_update_chunk_datasets returns False when task doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            batch_update_chunk_datasets,
        )

        mock_exists.return_value = False

        result = batch_update_chunk_datasets(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
            updates={"transcript": "Updated"},
        )

        assert result is False

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunks.task_exists")
    def test_batch_update_returns_false_when_chunk_not_found(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
        mock_h5_lock: MagicMock,
    ) -> None:
        """Test batch_update_chunk_datasets returns False when chunk doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import (
            batch_update_chunk_datasets,
        )

        mock_exists.return_value = True

        # Mock HDF5 file where chunk doesn't exist
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = batch_update_chunk_datasets(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
            updates={"transcript": "Updated"},
        )

        assert result is False
