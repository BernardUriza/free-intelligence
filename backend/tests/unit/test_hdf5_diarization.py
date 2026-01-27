"""Unit tests for HDF5 diarization module.

Tests cover diarization segment storage operations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# SAVE SEGMENTS TESTS
# ==============================================================================


class TestSaveDiarizationSegments:
    """Tests for save_diarization_segments function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5")
    def test_save_segments_raises_when_no_task(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test save_diarization_segments raises when task doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            save_diarization_segments,
        )

        # Mock HDF5 file without task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="does not exist"):
            save_diarization_segments(
                session_id="session-123",
                segments=[],
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5")
    def test_save_segments_creates_segments_group(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test save_diarization_segments creates segments group."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            save_diarization_segments,
        )

        # Mock segment
        mock_speaker = MagicMock()
        mock_speaker.speaker_id = "Speaker 1"

        mock_segment = MagicMock()
        mock_segment.speaker = mock_speaker
        mock_segment.text = "Hello world"
        mock_segment.start_time = 0.0
        mock_segment.end_time = 1.5
        mock_segment.confidence = 0.95
        mock_segment.improved_text = "Hello, world!"

        # Mock task group
        mock_seg_group = MagicMock()
        mock_seg_group.create_dataset = MagicMock()

        mock_segments_group = MagicMock()
        mock_segments_group.create_group = MagicMock(return_value=mock_seg_group)

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)  # no segments
        mock_task_group.create_group = MagicMock(return_value=mock_segments_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)  # task exists
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        path = save_diarization_segments(
            session_id="session-123",
            segments=[mock_segment],
        )

        assert path == "/sessions/session-123/tasks/DIARIZATION/segments"

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5")
    def test_save_segments_deletes_existing(
        self,
        mock_locked: MagicMock,
    ) -> None:
        """Test save_diarization_segments deletes existing segments."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            save_diarization_segments,
        )

        # Mock segments group
        mock_segments_group = MagicMock()
        mock_segments_group.create_group = MagicMock(return_value=MagicMock())

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)  # has segments
        mock_task_group.__delitem__ = MagicMock()
        mock_task_group.create_group = MagicMock(return_value=mock_segments_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)  # task exists
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        save_diarization_segments(
            session_id="session-123",
            segments=[],
        )

        # Verify delete was called
        mock_task_group.__delitem__.assert_called_with("segments")


# ==============================================================================
# GET SEGMENTS TESTS
# ==============================================================================


class TestGetDiarizationSegments:
    """Tests for get_diarization_segments function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.CORPUS_PATH")
    def test_get_segments_raises_when_no_corpus(
        self,
        mock_corpus_path: MagicMock,
    ) -> None:
        """Test get_diarization_segments raises when corpus doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            get_diarization_segments,
        )

        mock_corpus_path.exists.return_value = False

        with pytest.raises(ValueError, match="Corpus file not found"):
            get_diarization_segments("session-123")

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.CORPUS_PATH")
    def test_get_segments_raises_when_no_task(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_diarization_segments raises when task doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            get_diarization_segments,
        )

        mock_corpus_path.exists.return_value = True

        # Mock HDF5 file without task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="not found"):
            get_diarization_segments("session-123")

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.open_h5_read")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.CORPUS_PATH")
    def test_get_segments_raises_when_no_segments_group(
        self,
        mock_corpus_path: MagicMock,
        mock_open_h5: MagicMock,
    ) -> None:
        """Test get_diarization_segments raises when no segments."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            get_diarization_segments,
        )

        mock_corpus_path.exists.return_value = True

        # Mock task group without segments
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_open_h5.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_h5.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No segments found"):
            get_diarization_segments("session-123")


# ==============================================================================
# UPDATE SEGMENT TEXT TESTS
# ==============================================================================


class TestUpdateDiarizationSegmentText:
    """Tests for update_diarization_segment_text function."""

    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.get_session_h5_path"
    )
    def test_update_segment_raises_when_no_file(
        self,
        mock_get_path: MagicMock,
    ) -> None:
        """Test update_diarization_segment_text raises when file doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            update_diarization_segment_text,
        )
        from pathlib import Path

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path

        with pytest.raises(ValueError, match="Session file not found"):
            update_diarization_segment_text(
                session_id="session-123",
                segment_index=0,
                new_text="Updated text",
            )

    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5"
    )
    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.get_session_h5_path"
    )
    def test_update_segment_raises_when_no_task(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_diarization_segment_text raises when task doesn't exist."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            update_diarization_segment_text,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Mock HDF5 file without task
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="not found"):
            update_diarization_segment_text(
                session_id="session-123",
                segment_index=0,
                new_text="Updated text",
            )

    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5"
    )
    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.get_session_h5_path"
    )
    def test_update_segment_raises_when_no_segments(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_diarization_segment_text raises when no segments."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            update_diarization_segment_text,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Mock task group without segments
        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=False)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="No segments"):
            update_diarization_segment_text(
                session_id="session-123",
                segment_index=0,
                new_text="Updated text",
            )

    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5"
    )
    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.get_session_h5_path"
    )
    def test_update_segment_raises_when_segment_not_found(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_diarization_segment_text raises when segment not found."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            update_diarization_segment_text,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Mock segments group without the specific segment
        mock_segments_group = MagicMock()
        mock_segments_group.__contains__ = MagicMock(return_value=False)

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_segments_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="Segment 0 not found"):
            update_diarization_segment_text(
                session_id="session-123",
                segment_index=0,
                new_text="Updated text",
            )

    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.locked_session_h5"
    )
    @patch(
        "backend.src.fi_storage.infrastructure.hdf5.tasks.diarization.get_session_h5_path"
    )
    def test_update_segment_success(
        self,
        mock_get_path: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test update_diarization_segment_text successfully updates."""
        # FIXME: Broken import - use DI container instead
        # from infrastructure.storage.infrastructure.hdf5.tasks.diarization import (
            update_diarization_segment_text,
        )

        # Mock file exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        # Mock segment group
        mock_seg_group = MagicMock()
        mock_seg_group.__contains__ = MagicMock(return_value=True)  # has text
        mock_seg_group.__delitem__ = MagicMock()
        mock_seg_group.create_dataset = MagicMock()

        mock_segments_group = MagicMock()
        mock_segments_group.__contains__ = MagicMock(return_value=True)
        mock_segments_group.__getitem__ = MagicMock(return_value=mock_seg_group)

        mock_task_group = MagicMock()
        mock_task_group.__contains__ = MagicMock(return_value=True)
        mock_task_group.__getitem__ = MagicMock(return_value=mock_segments_group)

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_task_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise
        update_diarization_segment_text(
            session_id="session-123",
            segment_index=0,
            new_text="Updated text",
        )

        # Verify create_dataset was called
        mock_seg_group.create_dataset.assert_called()
