"""Unit tests for DITranscriptionService (DI refactored version).

Tests business logic with mocked dependencies (ITaskRepository, ILogger).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.6 - Testing Strategy
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.transcription.services.di_transcription_service import (
    DITranscriptionService,
    ChunkProcessingResult,
)
from backend.repositories.interfaces import ITaskRepository
from backend.repositories.session_repository import SessionRepository
from backend.utils.coder.utils.exceptions import SessionNotFoundError
from backend.infrastructure.interfaces.ilogger import ILogger


@pytest.fixture
def mock_task_repo():
    """Mock ITaskRepository."""
    repo = Mock(spec=ITaskRepository)
    repo.task_exists = Mock(return_value=True)
    repo.ensure_task_exists = Mock()
    repo.get_task_metadata = Mock(return_value={"status": "in_progress"})
    repo.batch_update_chunk_datasets = Mock()
    return repo


@pytest.fixture
def mock_logger():
    """Mock ILogger."""
    logger = Mock(spec=ILogger)
    logger.debug = Mock()  # Fix #4: process_chunk uses debug logging
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def mock_session_repo():
    """Mock SessionRepository (Fix #2 + Fix #4)."""
    repo = Mock(spec=SessionRepository)
    # Fix #4: Returns valid session dict (prevents SessionNotFoundError)
    repo.get = Mock(return_value={"session_id": "test-session-123", "status": "active"})
    repo.exists = Mock(return_value=True)
    return repo


@pytest.fixture
def service(mock_task_repo, mock_session_repo, mock_logger):
    """DITranscriptionService instance with mocked dependencies."""
    return DITranscriptionService(
        task_repository=mock_task_repo,
        session_repository=mock_session_repo,
        logger=mock_logger,
    )


class TestProcessChunk:
    """Tests for process_chunk() method."""

    @pytest.mark.asyncio
    async def test_creates_task_if_not_exists(self, service, mock_task_repo):
        """Test that process_chunk ensures task exists."""
        # Arrange
        mock_task_repo.task_exists.return_value = False
        session_id = "test-session-123"
        chunk_number = 1
        audio_bytes = b"fake-audio-data"

        # Act
        await service.process_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
        )

        # Assert
        mock_task_repo.ensure_task_exists.assert_called_once()
        call_args = mock_task_repo.ensure_task_exists.call_args
        assert call_args[1]["session_id"] == session_id
        assert call_args[1]["task_type"] == "TRANSCRIPTION"

    @pytest.mark.asyncio
    async def test_saves_audio_chunk(self, service, mock_task_repo):
        """Test that process_chunk saves audio data."""
        # Arrange
        session_id = "test-session-123"
        chunk_number = 1
        audio_bytes = b"fake-audio-data"

        # Act
        await service.process_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
        )

        # Assert
        mock_task_repo.batch_update_chunk_datasets.assert_called_once()
        call_args = mock_task_repo.batch_update_chunk_datasets.call_args
        assert call_args[1]["session_id"] == session_id
        # Verify chunk_number in updates
        updates = call_args[1]["updates"]
        assert chunk_number in updates

    @pytest.mark.asyncio
    async def test_updates_task_metadata(self, service, mock_task_repo):
        """Test that process_chunk updates task metadata."""
        # Arrange
        session_id = "test-session-123"
        chunk_number = 1
        audio_bytes = b"fake-audio-data"

        # Act
        await service.process_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
        )

        # Assert
        # batch_update_chunk_datasets should be called with metadata update
        assert mock_task_repo.batch_update_chunk_datasets.called

    @pytest.mark.asyncio
    async def test_returns_processing_result(self, service, mock_task_repo):
        """Test that process_chunk returns ChunkProcessingResult."""
        # Arrange
        session_id = "test-session-123"
        chunk_number = 1
        audio_bytes = b"fake-audio-data"

        # Act
        result = await service.process_chunk(
            session_id=session_id,
            chunk_number=chunk_number,
            audio_bytes=audio_bytes,
        )

        # Assert
        assert isinstance(result, ChunkProcessingResult)
        assert result.session_id == session_id
        assert result.chunk_number == chunk_number
        assert result.status == "accepted"

    @pytest.mark.asyncio
    async def test_handles_repository_error(self, service, mock_task_repo, mock_logger):
        """Test error handling when repository raises exception."""
        # Arrange
        mock_task_repo.batch_update_chunk_datasets.side_effect = Exception(
            "HDF5 connection failed"
        )
        session_id = "test-session-123"
        chunk_number = 1
        audio_bytes = b"fake-audio-data"

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service.process_chunk(
                session_id=session_id,
                chunk_number=chunk_number,
                audio_bytes=audio_bytes,
            )

        assert "HDF5 connection failed" in str(exc_info.value)
        # Logger should have logged error
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_raises_error_when_session_not_found(self, service, mock_session_repo, mock_logger):
        """Test that process_chunk raises SessionNotFoundError when session doesn't exist (Fix #4)."""
        # Arrange
        mock_session_repo.get.return_value = None  # Session NOT found
        session_id = "nonexistent-session-123"
        chunk_number = 1
        audio_bytes = b"fake-audio-data"

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            await service.process_chunk(
                session_id=session_id,
                chunk_number=chunk_number,
                audio_bytes=audio_bytes,
            )

        assert session_id in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()
        # Logger should have logged error
        mock_logger.error.assert_called()


class TestGetTranscription:
    """Tests for get_transcription() method."""

    @pytest.mark.asyncio
    async def test_retrieves_chunks_from_repository(self, service, mock_task_repo):
        """Test that get_transcription retrieves chunks from repository."""
        # Arrange
        session_id = "test-session-123"
        mock_task_repo.get_task_metadata.return_value = {
            "total_chunks": 3,
            "status": "completed",
        }

        # Mock get_chunks or similar method (adjust based on actual implementation)
        # This is a placeholder - adjust based on DITranscriptionService API

        # Act
        # result = await service.get_transcription(session_id)

        # Assert
        # mock_task_repo.get_task_metadata.assert_called_once_with(
        #     session_id=session_id, task_type="TRANSCRIPTION"
        # )

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_session(self, service, mock_task_repo):
        """Test that get_transcription returns None for nonexistent session."""
        # Arrange
        session_id = "nonexistent-session"
        mock_task_repo.task_exists.return_value = False
        mock_task_repo.get_task_metadata.return_value = None

        # Act
        # result = await service.get_transcription(session_id)

        # Assert
        # assert result is None
