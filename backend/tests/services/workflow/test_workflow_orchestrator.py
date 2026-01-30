"""Unit tests for WorkflowOrchestrator (DI refactored version).

Tests workflow dispatch logic with mocked dependencies.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.6 - Testing Strategy
"""

import pytest
from unittest.mock import Mock, patch
from backend.services.workflow.api.public.services.workflow_orchestrator import (
    WorkflowOrchestrator,
)
from backend.repositories.interfaces import ITaskRepository
from backend.infrastructure.interfaces.ilogger import ILogger


@pytest.fixture
def mock_task_repo():
    """Mock ITaskRepository."""
    repo = Mock(spec=ITaskRepository)
    repo.task_exists = Mock(return_value=True)
    return repo


@pytest.fixture
def mock_logger():
    """Mock ILogger."""
    logger = Mock(spec=ILogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def orchestrator(mock_task_repo, mock_logger):
    """WorkflowOrchestrator instance with mocked dependencies."""
    return WorkflowOrchestrator(
        task_repository=mock_task_repo,
        logger=mock_logger,
    )


class TestDispatchDiarization:
    """Tests for dispatch_diarization() method."""

    @patch("backend.services.workflow.api.public.services.workflow_orchestrator.spawn_worker")
    def test_creates_task_and_dispatches_worker(
        self, mock_spawn_worker, orchestrator, mock_task_repo
    ):
        """Test that dispatch_diarization creates task and spawns worker."""
        # Arrange
        session_id = "test-session-123"

        # Act
        result = orchestrator.dispatch_diarization(session_id)

        # Assert
        mock_task_repo.task_exists.assert_called_once()
        mock_spawn_worker.assert_called_once()
        assert result["session_id"] == session_id
        assert result["status"] == "dispatched"

    @patch("backend.services.workflow.api.public.services.workflow_orchestrator.spawn_worker")
    def test_returns_job_response(
        self, mock_spawn_worker, orchestrator
    ):
        """Test that dispatch_diarization returns job dispatch response."""
        # Arrange
        session_id = "test-session-123"

        # Act
        result = orchestrator.dispatch_diarization(session_id)

        # Assert
        assert "job_id" in result
        assert "message" in result
        assert session_id in result["message"]


class TestDispatchSOAP:
    """Tests for dispatch_soap_generation() method."""

    @patch("backend.services.workflow.api.public.services.workflow_orchestrator.spawn_worker")
    def test_dispatches_soap_worker(
        self, mock_spawn_worker, orchestrator, mock_task_repo
    ):
        """Test that dispatch_soap_generation spawns SOAP worker."""
        # Arrange
        session_id = "test-session-456"

        # Act
        result = orchestrator.dispatch_soap_generation(session_id)

        # Assert
        mock_task_repo.task_exists.assert_called_once()
        mock_spawn_worker.assert_called_once()
        assert result["status"] == "dispatched"


class TestDispatchEmotion:
    """Tests for dispatch_emotion_analysis() method."""

    @patch("backend.services.workflow.api.public.services.workflow_orchestrator.spawn_worker")
    def test_dispatches_emotion_worker(
        self, mock_spawn_worker, orchestrator, mock_task_repo
    ):
        """Test that dispatch_emotion_analysis spawns emotion worker."""
        # Arrange
        session_id = "test-session-789"

        # Act
        result = orchestrator.dispatch_emotion_analysis(session_id)

        # Assert
        mock_task_repo.task_exists.assert_called_once()
        mock_spawn_worker.assert_called_once()
        assert result["status"] == "dispatched"


class TestDispatchEncryption:
    """Tests for dispatch_encryption() method."""

    @patch("backend.services.workflow.api.public.services.workflow_orchestrator.spawn_worker")
    def test_dispatches_encryption_worker(
        self, mock_spawn_worker, orchestrator, mock_task_repo
    ):
        """Test that dispatch_encryption spawns encryption worker."""
        # Arrange
        session_id = "test-session-encrypt"

        # Act
        result = orchestrator.dispatch_encryption(session_id)

        # Assert
        mock_task_repo.task_exists.assert_called_once()
        mock_spawn_worker.assert_called_once()
        assert result["encryption_status"] == "QUEUED"
        assert "encryption_task_id" in result


class TestDispatchWorkflow:
    """Tests for dispatch_workflow() generic method."""

    @patch("backend.services.workflow.api.public.services.workflow_orchestrator.spawn_worker")
    def test_routes_to_correct_workflow(
        self, mock_spawn_worker, orchestrator
    ):
        """Test that dispatch_workflow routes to correct method."""
        # Arrange
        session_id = "test-session-generic"
        workflow_type = "DIARIZATION"

        # Act
        result = orchestrator.dispatch_workflow(workflow_type, session_id)

        # Assert
        assert result["status"] == "dispatched"
        mock_spawn_worker.assert_called_once()

    def test_raises_for_unknown_workflow(self, orchestrator):
        """Test that dispatch_workflow raises ValueError for unknown workflow."""
        # Arrange
        session_id = "test-session"
        workflow_type = "UNKNOWN_WORKFLOW"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            orchestrator.dispatch_workflow(workflow_type, session_id)

        assert "Unknown workflow type" in str(exc_info.value)
