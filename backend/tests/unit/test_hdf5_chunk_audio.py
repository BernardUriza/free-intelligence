"""Unit tests for HDF5 chunk_audio module.

Tests cover audio blob storage for transcription chunks.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# ADD AUDIO TESTS
# ==============================================================================


class TestAddAudioToChunk:
    """Tests for add_audio_to_chunk function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.CORPUS_PATH")
    def test_add_audio_raises_when_chunk_not_exists(
        self,
        mock_corpus_path: MagicMock,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test add_audio_to_chunk raises when chunk doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
            add_audio_to_chunk,
        )

        mock_corpus_path.parent.mkdir = MagicMock()

        # Mock HDF5 file without chunk
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(ValueError, match="does not exist"):
            add_audio_to_chunk(
                session_id="session-123",
                chunk_idx=0,
                audio_bytes=b"audio data",
            )

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.CORPUS_PATH")
    def test_add_audio_creates_dataset(
        self,
        mock_corpus_path: MagicMock,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test add_audio_to_chunk creates audio dataset."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
            add_audio_to_chunk,
        )

        mock_corpus_path.parent.mkdir = MagicMock()

        # Mock chunk group
        mock_chunk_group = MagicMock()
        mock_chunk_group.__contains__ = MagicMock(return_value=False)  # no existing audio
        mock_chunk_group.create_dataset = MagicMock()

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)  # chunk exists
        mock_file.__getitem__ = MagicMock(return_value=mock_chunk_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        path = add_audio_to_chunk(
            session_id="session-123",
            chunk_idx=0,
            audio_bytes=b"audio data",
        )

        assert "audio.webm" in path

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.CORPUS_PATH")
    def test_add_audio_deletes_existing(
        self,
        mock_corpus_path: MagicMock,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test add_audio_to_chunk deletes existing audio."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
            add_audio_to_chunk,
        )

        mock_corpus_path.parent.mkdir = MagicMock()

        # Mock chunk group with existing audio
        mock_chunk_group = MagicMock()
        mock_chunk_group.__contains__ = MagicMock(return_value=True)  # has existing audio
        mock_chunk_group.__delitem__ = MagicMock()
        mock_chunk_group.create_dataset = MagicMock()

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)  # chunk exists
        mock_file.__getitem__ = MagicMock(return_value=mock_chunk_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        add_audio_to_chunk(
            session_id="session-123",
            chunk_idx=0,
            audio_bytes=b"new audio data",
        )

        # Verify delete was called
        mock_chunk_group.__delitem__.assert_called()

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.locked_session_h5")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio._h5_lock")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.CORPUS_PATH")
    def test_add_audio_custom_filename(
        self,
        mock_corpus_path: MagicMock,
        mock_h5_lock: MagicMock,
        mock_locked: MagicMock,
    ) -> None:
        """Test add_audio_to_chunk uses custom filename."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
            add_audio_to_chunk,
        )

        mock_corpus_path.parent.mkdir = MagicMock()

        # Mock chunk group
        mock_chunk_group = MagicMock()
        mock_chunk_group.__contains__ = MagicMock(return_value=False)
        mock_chunk_group.create_dataset = MagicMock()

        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=True)
        mock_file.__getitem__ = MagicMock(return_value=mock_chunk_group)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        path = add_audio_to_chunk(
            session_id="session-123",
            chunk_idx=0,
            audio_bytes=b"audio data",
            filename="custom.mp3",
        )

        assert "custom.mp3" in path


# ==============================================================================
# GET AUDIO TESTS
# ==============================================================================


class TestGetChunkAudioBytes:
    """Tests for get_chunk_audio_bytes function."""

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.CORPUS_PATH")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.locked_session_h5")
    def test_get_audio_returns_none_when_no_session_and_no_corpus(
        self,
        mock_locked: MagicMock,
        mock_corpus_path: MagicMock,
    ) -> None:
        """Test get_chunk_audio_bytes returns None when file doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
            get_chunk_audio_bytes,
        )

        # Session lock fails (no session file)
        mock_locked.return_value.__enter__ = MagicMock(side_effect=Exception("No file"))

        # Corpus doesn't exist
        mock_corpus_path.exists.return_value = False
        mock_corpus_path.parent.mkdir = MagicMock()

        result = get_chunk_audio_bytes(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
        )

        assert result is None

    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.CORPUS_PATH")
    @patch("backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio.locked_session_h5")
    def test_get_audio_returns_none_when_no_chunk(
        self,
        mock_locked: MagicMock,
        mock_corpus_path: MagicMock,
    ) -> None:
        """Test get_chunk_audio_bytes returns None when chunk doesn't exist."""
        from backend.models.task_type import TaskType
        from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
            get_chunk_audio_bytes,
        )

        mock_corpus_path.parent.mkdir = MagicMock()
        mock_corpus_path.exists.return_value = False

        # Mock HDF5 file without chunk
        mock_file = MagicMock()
        mock_file.__contains__ = MagicMock(return_value=False)

        mock_locked.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_locked.return_value.__exit__ = MagicMock(return_value=False)

        result = get_chunk_audio_bytes(
            session_id="session-123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=0,
        )

        assert result is None
