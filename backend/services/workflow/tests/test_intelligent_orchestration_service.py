"""Unit tests for IntelligentOrchestrationService.

Tests business logic with mocked dependencies (no real workers/storage).

Pattern:
- Mock all dependencies (orchestrator, router, tracker, repositories, logger)
- Test service methods in isolation
- Verify service calls correct dependencies with correct arguments
- Test error handling (FileNotFoundError, ValueError)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.workflow.constants import (
    AUDIO_BITRATE_BYTES_PER_SECOND,
    DEFAULT_AUDIO_DURATION_SECONDS,
    WORKFLOW_DIARIZATION,
    WORKFLOW_EMOTION,
    WORKFLOW_SOAP,
    WORKFLOW_TRANSCRIPTION,
)
from backend.services.workflow.services.intelligent_orchestration_service import (
    IntelligentOrchestrationService,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIXTURES (Mocked Dependencies)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture
def mock_orchestrator():
    """Mock WorkflowOrchestrator (async methods)."""
    orchestrator = MagicMock()
    orchestrator.dispatch_diarization = AsyncMock(return_value={"task_id": "task-123", "status": "dispatched"})
    orchestrator.dispatch_soap_generation = AsyncMock(return_value={"task_id": "task-456", "status": "dispatched"})
    orchestrator.dispatch_emotion_analysis = AsyncMock(return_value={"task_id": "task-789", "status": "dispatched"})
    return orchestrator


@pytest.fixture
def mock_router():
    """Mock WorkflowRouter (sync methods)."""
    router = MagicMock()
    router.route_workflows.return_value = {
        "workflows": [WORKFLOW_DIARIZATION, WORKFLOW_SOAP],
        "reasoning": "Audio >60s requires diarization. SOAP note generation enabled.",
        "parallel": True,
        "cost": {
            "routing_cost_usd": 0.00003,
            "execution_tokens_saved": 1500,
            "execution_cost_saved_usd": 0.0045,
        },
        "estimated_duration_seconds": 120,
    }
    return router


@pytest.fixture
def mock_tracker():
    """Mock WorkflowTracker (sync methods)."""
    tracker = MagicMock()
    tracker.mark_task_started.return_value = None
    tracker.mark_task_completed.return_value = None
    tracker.is_workflow_complete.return_value = True
    return tracker


@pytest.fixture
def mock_task_repo():
    """Mock ITaskRepository."""
    repo = MagicMock()
    repo.ensure_task_exists.return_value = "task-123"
    repo.get_task_metadata.return_value = {"status": "completed"}
    return repo


@pytest.fixture
def mock_corpus_repo():
    """Mock ICorpusRepository."""
    repo = MagicMock()
    # Simulate 3-minute audio file (180 seconds * 12KB/s = 2,160,000 bytes)
    audio_data = b"x" * int(180 * AUDIO_BITRATE_BYTES_PER_SECOND)
    repo.get_session_audio.return_value = audio_data
    repo.list_session_tasks.return_value = ["transcription"]  # Only transcription completed
    return repo


@pytest.fixture
def mock_logger():
    """Mock ILogger."""
    logger = MagicMock()
    logger.info.return_value = None
    logger.warning.return_value = None
    logger.error.return_value = None
    return logger


@pytest.fixture
def service(mock_orchestrator, mock_router, mock_tracker, mock_task_repo, mock_corpus_repo, mock_logger):
    """Create IntelligentOrchestrationService with mocked dependencies."""
    return IntelligentOrchestrationService(
        orchestrator=mock_orchestrator,
        router=mock_router,
        tracker=mock_tracker,
        task_repository=mock_task_repo,
        corpus_repository=mock_corpus_repo,
        logger=mock_logger,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: orchestrate_intelligent_workflow
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_orchestrate_intelligent_workflow_success(service, mock_router, mock_orchestrator):
    """Test successful workflow orchestration with audio detection."""
    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
        user_intent=None,
    )

    # Verify routing was called with detected audio duration
    mock_router.route_workflows.assert_called_once()
    call_args = mock_router.route_workflows.call_args
    assert call_args.kwargs["session_id"] == "session-123"
    assert call_args.kwargs["audio_duration_seconds"] == pytest.approx(180.0, rel=0.1)
    assert call_args.kwargs["language"] == "es"
    assert call_args.kwargs["existing_tasks"] == ["transcription"]

    # Verify orchestrator dispatched workflows
    assert mock_orchestrator.dispatch_diarization.call_count == 1
    assert mock_orchestrator.dispatch_soap_generation.call_count == 1

    # Verify response structure
    assert result["session_id"] == "session-123"
    assert result["status"] == "dispatched"
    assert WORKFLOW_DIARIZATION in result["workflows_dispatched"]
    assert WORKFLOW_SOAP in result["workflows_dispatched"]
    assert "task_ids" in result
    assert "routing_decision" in result
    assert "cost" in result


@pytest.mark.asyncio
async def test_audio_duration_detection_fallback(service, mock_corpus_repo):
    """Test fallback to default duration when audio detection fails."""
    # Simulate audio file not found
    mock_corpus_repo.get_session_audio.side_effect = FileNotFoundError("Audio not found")

    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/nonexistent.wav",
        language="es",
    )

    # Verify fallback duration was used (60s default)
    assert result["audio_duration_seconds"] == DEFAULT_AUDIO_DURATION_SECONDS


@pytest.mark.asyncio
async def test_audio_duration_detection_empty_audio(service, mock_corpus_repo):
    """Test fallback when audio data is empty/None."""
    # Simulate empty audio data
    mock_corpus_repo.get_session_audio.return_value = None

    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
    )

    # Verify fallback duration was used
    assert result["audio_duration_seconds"] == DEFAULT_AUDIO_DURATION_SECONDS


@pytest.mark.asyncio
async def test_existing_tasks_detection(service, mock_corpus_repo, mock_task_repo):
    """Test detection of completed tasks to avoid duplicates."""
    # Simulate multiple completed tasks
    mock_corpus_repo.list_session_tasks.return_value = ["transcription", "diarization"]
    mock_task_repo.get_task_metadata.side_effect = [
        {"status": "completed"},  # transcription completed
        {"status": "completed"},  # diarization completed
    ]

    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
    )

    # Verify router received existing tasks
    call_args = service.router.route_workflows.call_args
    assert "transcription" in call_args.kwargs["existing_tasks"]
    assert "diarization" in call_args.kwargs["existing_tasks"]


@pytest.mark.asyncio
async def test_existing_tasks_detection_failure(service, mock_corpus_repo):
    """Test graceful handling when existing tasks detection fails."""
    # Simulate repository error
    mock_corpus_repo.list_session_tasks.side_effect = Exception("DB error")

    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
    )

    # Verify orchestration continues with empty existing_tasks
    call_args = service.router.route_workflows.call_args
    assert call_args.kwargs["existing_tasks"] == []


@pytest.mark.asyncio
async def test_workflow_dispatch_skips_transcription(service, mock_router, mock_orchestrator):
    """Test that TRANSCRIPTION workflow is skipped (handled during upload)."""
    # Router includes TRANSCRIPTION in decision
    mock_router.route_workflows.return_value = {
        "workflows": [WORKFLOW_TRANSCRIPTION, WORKFLOW_DIARIZATION],
        "reasoning": "Test",
        "parallel": True,
        "cost": {"routing_cost_usd": 0.00003, "execution_tokens_saved": 0, "execution_cost_saved_usd": 0},
    }

    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
    )

    # Verify TRANSCRIPTION was NOT dispatched
    assert mock_orchestrator.dispatch_diarization.call_count == 1
    assert WORKFLOW_TRANSCRIPTION in result["existing_tasks_skipped"]
    assert WORKFLOW_TRANSCRIPTION not in result["workflows_dispatched"]


@pytest.mark.asyncio
async def test_workflow_dispatch_handles_partial_failure(service, mock_orchestrator, mock_logger):
    """Test that dispatch continues even if one workflow fails."""
    # Simulate diarization dispatch failure
    mock_orchestrator.dispatch_diarization.side_effect = Exception("Worker pool full")

    result = await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
    )

    # Verify SOAP was still dispatched (partial success)
    assert mock_orchestrator.dispatch_soap_generation.call_count == 1

    # Verify error was logged
    mock_logger.error.assert_called()
    assert "WORKFLOW_DISPATCH_FAILED" in str(mock_logger.error.call_args)


@pytest.mark.asyncio
async def test_user_intent_passed_to_router(service, mock_router):
    """Test that user_intent is passed to router for decision-making."""
    await service.orchestrate_intelligent_workflow(
        session_id="session-123",
        audio_file_path="/tmp/audio.wav",
        language="es",
        user_intent="quick consult",
    )

    # Verify router received user_intent
    call_args = mock_router.route_workflows.call_args
    assert call_args.kwargs["user_intent"] == "quick consult"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: _detect_audio_duration (private method)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_detect_audio_duration_success(service, mock_corpus_repo):
    """Test audio duration detection from file metadata."""
    # 3-minute audio file (180 seconds)
    audio_data = b"x" * int(180 * AUDIO_BITRATE_BYTES_PER_SECOND)
    mock_corpus_repo.get_session_audio.return_value = audio_data

    duration = await service._detect_audio_duration("session-123", "/tmp/audio.wav")

    assert duration == pytest.approx(180.0, rel=0.1)


@pytest.mark.asyncio
async def test_detect_audio_duration_file_not_found(service, mock_corpus_repo):
    """Test fallback when audio file doesn't exist."""
    mock_corpus_repo.get_session_audio.side_effect = FileNotFoundError("Not found")

    duration = await service._detect_audio_duration("session-123", "/tmp/nonexistent.wav")

    assert duration == DEFAULT_AUDIO_DURATION_SECONDS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTS: _get_existing_task_types (private method)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_get_existing_task_types_completed_only(service, mock_corpus_repo, mock_task_repo):
    """Test that only completed tasks are returned."""
    mock_corpus_repo.list_session_tasks.return_value = ["transcription", "diarization", "soap_generation"]
    mock_task_repo.get_task_metadata.side_effect = [
        {"status": "completed"},  # transcription
        {"status": "in_progress"},  # diarization (skip)
        {"status": "completed"},  # soap_generation
    ]

    existing = await service._get_existing_task_types("session-123")

    assert "transcription" in existing
    assert "soap_generation" in existing
    assert "diarization" not in existing  # Not completed


@pytest.mark.asyncio
async def test_get_existing_task_types_handles_invalid_task_type(service, mock_corpus_repo):
    """Test graceful handling of invalid task types."""
    mock_corpus_repo.list_session_tasks.return_value = ["invalid_task_type", "transcription"]

    existing = await service._get_existing_task_types("session-123")

    # Invalid task type should be skipped (no error)
    assert "transcription" in existing
    assert "invalid_task_type" not in existing
