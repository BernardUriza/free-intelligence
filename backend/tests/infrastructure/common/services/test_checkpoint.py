"""Tests for CheckpointService - audio concatenation at pause events.

Author: Claude Code
Created: 2026-02-02
"""

from unittest.mock import Mock

import pytest

from backend.infrastructure.common.services.checkpoint import (
    AudioConcatenationError,
    CheckpointRequest,
    CheckpointService,
    NoChunksToProcessError,
    TooManyChunksError,
)


class TestCheckpointRequest:
    """Tests for CheckpointRequest DTO validation."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        req = CheckpointRequest(
            session_id="test-session-123",
            last_checkpoint_idx=-1,
            new_checkpoint_idx=5,
        )
        assert req.chunk_range == (0, 5)
        assert req.expected_chunk_count == 6

    def test_valid_request_mid_session(self) -> None:
        """Test request for mid-session checkpoint."""
        req = CheckpointRequest(
            session_id="session-abc",
            last_checkpoint_idx=10,
            new_checkpoint_idx=20,
        )
        assert req.chunk_range == (11, 20)
        assert req.expected_chunk_count == 10

    def test_invalid_short_session_id(self) -> None:
        """Test that short session_id raises ValueError."""
        with pytest.raises(ValueError, match="at least 5 characters"):
            CheckpointRequest(
                session_id="abc",
                last_checkpoint_idx=-1,
                new_checkpoint_idx=5,
            )

    def test_invalid_last_checkpoint_idx(self) -> None:
        """Test that last_checkpoint_idx < -1 raises ValueError."""
        with pytest.raises(ValueError, match="must be >= -1"):
            CheckpointRequest(
                session_id="test-session",
                last_checkpoint_idx=-2,
                new_checkpoint_idx=5,
            )

    def test_invalid_new_checkpoint_idx_negative(self) -> None:
        """Test that new_checkpoint_idx < 0 raises ValueError."""
        with pytest.raises(ValueError, match="must be >= 0"):
            CheckpointRequest(
                session_id="test-session",
                last_checkpoint_idx=-1,
                new_checkpoint_idx=-1,
            )

    def test_invalid_checkpoint_order(self) -> None:
        """Test that new <= last raises ValueError."""
        with pytest.raises(ValueError, match="must be > last"):
            CheckpointRequest(
                session_id="test-session",
                last_checkpoint_idx=5,
                new_checkpoint_idx=5,
            )


class TestCheckpointService:
    """Tests for CheckpointService execution."""

    @pytest.fixture
    def mock_repo(self) -> Mock:
        """Create mock audio chunk repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repo: Mock) -> CheckpointService:
        """Create service with mock repository."""
        return CheckpointService(mock_repo)

    def test_execute_success(self, service: CheckpointService, mock_repo: Mock) -> None:
        """Test successful checkpoint execution."""
        # Arrange
        mock_repo.get_audio_data_range.return_value = [
            b"chunk0",
            b"chunk1",
            b"chunk2",
        ]
        request = CheckpointRequest(
            session_id="test-session-123",
            last_checkpoint_idx=-1,
            new_checkpoint_idx=2,
        )

        # Act
        result = service.execute(request)

        # Assert
        assert result.chunks_concatenated == 3
        assert result.audio_bytes == b"chunk0chunk1chunk2"
        assert result.start_chunk == 0
        assert result.end_chunk == 2
        mock_repo.get_audio_data_range.assert_called_once_with(
            session_id="test-session-123",
            start_chunk=0,
            end_chunk=2,
        )

    def test_execute_no_chunks(self, service: CheckpointService, mock_repo: Mock) -> None:
        """Test that empty chunk list raises NoChunksToProcessError."""
        # Arrange
        mock_repo.get_audio_data_range.return_value = []
        request = CheckpointRequest(
            session_id="test-session-123",
            last_checkpoint_idx=-1,
            new_checkpoint_idx=5,
        )

        # Act & Assert
        with pytest.raises(NoChunksToProcessError, match="No chunks found"):
            service.execute(request)

    def test_execute_too_many_chunks(self, service: CheckpointService) -> None:
        """Test that requesting too many chunks raises TooManyChunksError."""
        # Arrange
        request = CheckpointRequest(
            session_id="test-session-123",
            last_checkpoint_idx=-1,
            new_checkpoint_idx=150,  # > MAX_CHUNKS_PER_CHECKPOINT (100)
        )

        # Act & Assert
        with pytest.raises(TooManyChunksError, match="exceeds limit"):
            service.execute(request)

    def test_execute_repo_error(self, service: CheckpointService, mock_repo: Mock) -> None:
        """Test that repository errors are wrapped in AudioConcatenationError."""
        # Arrange
        mock_repo.get_audio_data_range.side_effect = IOError("HDF5 file locked")
        request = CheckpointRequest(
            session_id="test-session-123",
            last_checkpoint_idx=-1,
            new_checkpoint_idx=5,
        )

        # Act & Assert
        with pytest.raises(AudioConcatenationError, match="Failed to retrieve"):
            service.execute(request)
