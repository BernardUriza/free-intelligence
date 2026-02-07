"""Unit tests for DIChatService (DI refactored version).

Tests business logic with mocked dependencies (PersonaManager, AuditService, PolicyLoader).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.6 - Testing Strategy
"""

import pytest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from backend.services.llm.services.di_chat_service import (
    DIChatService,
    ChatProcessingResult,
)
from backend.services.llm.services.persona.manager import PersonaManager
from backend.services.audit.services.audit_service import AuditService
from backend.policy.policy_loader import PolicyLoader
from backend.infrastructure.interfaces.ilogger import ILogger


def _make_llm_response(content="Hello", tokens=50, model="gpt-4"):
    """Create a mock LLM response object with .content, .usage, .model attrs."""
    usage = SimpleNamespace(total_tokens=tokens)
    return SimpleNamespace(content=content, usage=usage, model=model)


@pytest.fixture
def mock_persona_manager():
    """Mock PersonaManager."""
    mgr = Mock(spec=PersonaManager)
    mgr.route_persona = Mock(return_value="clinical_advisor")
    mgr.get_persona = Mock(
        return_value=Mock(
            voice="nova",
            cost_per_message=0.02,
            model="gpt-4",
        )
    )
    mgr.build_system_prompt = Mock(return_value="You are a clinical advisor.")
    return mgr


@pytest.fixture
def mock_audit_service():
    """Mock AuditService."""
    service = Mock(spec=AuditService)
    service.log_action = Mock()
    return service


@pytest.fixture
def mock_policy_loader():
    """Mock PolicyLoader."""
    loader = Mock(spec=PolicyLoader)
    loader.get_primary_provider = Mock(return_value="openai")
    return loader


@pytest.fixture
def mock_logger():
    """Mock ILogger."""
    logger = Mock(spec=ILogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def service(mock_persona_manager, mock_audit_service, mock_policy_loader, mock_logger):
    """DIChatService instance with mocked dependencies."""
    return DIChatService(
        persona_manager=mock_persona_manager,
        audit_service=mock_audit_service,
        policy_loader=mock_policy_loader,
        logger=mock_logger,
    )


class TestProcessChat:
    """Tests for process_chat() method."""

    @pytest.mark.asyncio
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    async def test_routes_persona_when_auto(
        self, mock_llm_generate, service, mock_persona_manager
    ):
        """Test that process_chat routes persona when persona='auto'."""
        # Arrange
        mock_llm_generate.return_value = _make_llm_response("Hello, how can I help?", 50, "gpt-4")
        message = "I need help with a patient"

        # Act
        result = await service.process_chat(
            message=message,
            persona="auto",
        )

        # Assert
        mock_persona_manager.route_persona.assert_called_once_with(message)
        assert result.persona == "clinical_advisor"

    @pytest.mark.asyncio
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    async def test_builds_prompt_without_memory(
        self, mock_llm_generate, service, mock_persona_manager
    ):
        """Test that process_chat builds prompt correctly without memory."""
        # Arrange
        mock_llm_generate.return_value = _make_llm_response("Response text", 100, "gpt-4")

        # Act
        await service.process_chat(
            message="Test message",
            persona="clinical_advisor",
            use_memory=False,
        )

        # Assert
        mock_persona_manager.build_system_prompt.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    async def test_calculates_cost(
        self, mock_llm_generate, service, mock_persona_manager
    ):
        """Test that process_chat calculates cost from persona config."""
        # Arrange
        mock_llm_generate.return_value = _make_llm_response("Response", 200, "gpt-4")
        mock_persona_manager.get_persona.return_value.cost_per_message = 0.05

        # Act
        result = await service.process_chat(
            message="Test",
            persona="clinical_advisor",
        )

        # Assert - cost is calculated from tokens: (200/1000) * 0.045 = 0.009
        assert result.cost_usd == pytest.approx(0.009, abs=0.001)

    @pytest.mark.asyncio
    async def test_validates_memory_requires_doctor_id(self, service):
        """Test that process_chat raises ValueError when memory enabled without doctor_id."""
        # Arrange
        message = "Test message"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await service.process_chat(
                message=message,
                persona="clinical_advisor",
                use_memory=True,
                doctor_id=None,  # Missing!
            )

        assert "doctor_id is required" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    async def test_returns_chat_processing_result(
        self, mock_llm_generate, service
    ):
        """Test that process_chat returns ChatProcessingResult with all fields."""
        # Arrange
        mock_llm_generate.return_value = _make_llm_response("Test response", 150, "gpt-4")

        # Act
        result = await service.process_chat(
            message="Test",
            persona="clinical_advisor",
        )

        # Assert
        assert isinstance(result, ChatProcessingResult)
        assert result.response_text == "Test response"
        assert result.tokens_used == 150
        assert result.model_name == "gpt-4"
        # Thinking is extracted from response metadata, not from the mock return value
        # Our simple mock doesn't include metadata, so thinking is None
        assert result.thinking is None
        assert result.cost_usd > 0
        assert result.latency_ms >= 0
        assert len(result.prompt_hash) == 12  # SHA256 truncated for logs
        assert len(result.response_hash) == 12

    @pytest.mark.asyncio
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    @patch("backend.services.llm.services.di_chat_service.get_memory_manager")
    async def test_enables_memory_for_azure(
        self, mock_get_memory, mock_llm_generate, service, mock_policy_loader
    ):
        """Test that process_chat auto-enables memory for Azure GPT-4."""
        # Arrange
        mock_policy_loader.get_primary_provider.return_value = "azure"
        mock_get_memory.return_value = None  # Embeddings unavailable
        mock_llm_generate.return_value = _make_llm_response("Response", 50, "gpt-4")

        # Act
        result = await service.process_chat(
            message="Test",
            persona="clinical_advisor",
            use_memory=False,  # Explicitly disabled
            doctor_id=None,  # No doctor_id provided
        )

        # Assert
        # Auto-memory should be attempted (but skipped if embeddings unavailable)
        assert result.auto_memory_enabled is True
        # Memory should NOT be enabled (embeddings unavailable)
        assert result.memory_enabled is False

    @pytest.mark.asyncio
    @patch("backend.services.llm.services.di_chat_service.llm_generate")
    async def test_logs_persona_usage_metric(
        self, mock_llm_generate, service, mock_audit_service
    ):
        """Test that process_chat logs persona usage to audit service."""
        # Arrange
        mock_llm_generate.return_value = _make_llm_response("Response", 100, "gpt-4")

        # Act
        await service.process_chat(
            message="Test",
            persona="clinical_advisor",
            doctor_id="doctor-123",
        )

        # Assert
        mock_audit_service.log_action.assert_called_once()
        call_args = mock_audit_service.log_action.call_args
        assert call_args[1]["action"] == "llm_call"
        assert call_args[1]["user_id"] == "doctor-123"
        assert "persona:clinical_advisor" in call_args[1]["resource"]
