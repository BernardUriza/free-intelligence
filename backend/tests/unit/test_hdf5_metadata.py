"""Unit tests for HDF5 metadata module.

Tests cover task metadata CRUD operations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# UPDATE METADATA TESTS
# ==============================================================================


class TestUpdateTaskMetadata:
    """Tests for update_task_metadata function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_update_metadata_fails_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test update_task_metadata raises when task doesn't exist."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            update_task_metadata,
        )

        mock_exists.return_value = False

        with pytest.raises(ValueError, match="does not exist"):
            update_task_metadata(
                session_id="session-123",
                task_type=TaskType.TRANSCRIPTION,
                metadata={"status": "completed"},
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_update_metadata_creates_new_metadata(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_task_metadata creates metadata when none exists."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            update_task_metadata,
        )

        mock_exists.return_value = True

        # Mock task group without existing metadata
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)  # no job_metadata
        mock_task_group.create_dataset = MagicMock()

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise
        update_task_metadata(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            metadata={"total_chunks": 5},
        )

        # Verify create_dataset was called
        mock_task_group.create_dataset.assert_called()

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_update_metadata_merges_with_existing(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_task_metadata merges with existing metadata."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            update_task_metadata,
        )

        mock_exists.return_value = True

        # Mock existing metadata - properly mock the dataset read
        existing_json = b'{"total_chunks": 5, "status": "pending"}'

        mock_metadata_dataset = MagicMock()
        mock_metadata_dataset.__getitem__ = MagicMock(
            return_value=MagicMock(__call__=MagicMock(return_value=existing_json))
        )

        # The dataset returns bytes when called with [()]
        class MockDataset:
            def __getitem__(self, key):
                return existing_json

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)  # has job_metadata
        mock_task_group.__getitem__ = MagicMock(return_value=MockDataset())
        mock_task_group.__delitem__ = MagicMock()
        mock_task_group.create_dataset = MagicMock()

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise
        update_task_metadata(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            metadata={"status": "completed"},
        )

        # Verify delete and create_dataset were called
        mock_task_group.__delitem__.assert_called()
        mock_task_group.create_dataset.assert_called()

    def test_update_metadata_with_string_task_type(self) -> None:
        """Test update_task_metadata accepts string task type."""
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            update_task_metadata,
        )

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists"
        ) as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(ValueError, match="does not exist"):
                update_task_metadata(
                    session_id="session-123",
                    task_type="TRANSCRIPTION",  # string instead of enum
                    metadata={"status": "completed"},
                )


# ==============================================================================
# GET METADATA TESTS
# ==============================================================================


class TestGetTaskMetadata:
    """Tests for get_task_metadata function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_get_metadata_returns_none_when_no_task(
        self,
        mock_exists: MagicMock,
    ) -> None:
        """Test get_task_metadata returns None when task doesn't exist."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            get_task_metadata,
        )

        mock_exists.return_value = False

        result = get_task_metadata("session-123", TaskType.TRANSCRIPTION)

        assert result is None

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_get_metadata_returns_none_when_no_metadata(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test get_task_metadata returns None when no metadata exists."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            get_task_metadata,
        )

        mock_exists.return_value = True

        # Mock task group without metadata
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = get_task_metadata("session-123", TaskType.TRANSCRIPTION)

        assert result is None

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_get_metadata_returns_metadata_dict(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test get_task_metadata returns metadata dictionary."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            get_task_metadata,
        )

        mock_exists.return_value = True

        # Mock metadata with proper dataset behavior
        metadata_json = b'{"total_chunks": 5, "status": "completed"}'

        class MockDataset:
            def __getitem__(self, key):
                return metadata_json

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=MockDataset())

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = get_task_metadata("session-123", TaskType.TRANSCRIPTION)

        assert result == {"total_chunks": 5, "status": "completed"}

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_get_metadata_handles_bytes_response(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test get_task_metadata handles bytes from HDF5."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            get_task_metadata,
        )

        mock_exists.return_value = True

        # Mock metadata as bytes (as returned by HDF5)
        metadata_bytes = b'{"total_chunks": 10}'

        class MockDataset:
            def __getitem__(self, key):
                return metadata_bytes

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=MockDataset())

        mock_file = MagicMock()
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = get_task_metadata("session-123", TaskType.TRANSCRIPTION)

        assert result == {"total_chunks": 10}

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists")
    def test_get_metadata_returns_none_on_exception(
        self,
        mock_exists: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test get_task_metadata returns None on exception."""
        from backend.models.task_type import TaskType
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            get_task_metadata,
        )

        mock_exists.return_value = True

        # Make locked_session_h5 raise exception
        mock_locked.return_value.__enter__ = MagicMock(side_effect=Exception("HDF5 error"))
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = get_task_metadata("session-123", TaskType.TRANSCRIPTION)

        assert result is None

    def test_get_metadata_with_string_task_type(self) -> None:
        """Test get_task_metadata accepts string task type."""
        from infrastructure.storage.infrastructure.hdf5.tasks.metadata import (
            get_task_metadata,
        )

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.metadata.task_exists"
        ) as mock_exists:
            mock_exists.return_value = False

            result = get_task_metadata("session-123", "TRANSCRIPTION")

            assert result is None
