"""
Unit tests for backend/providers/adapters.py

Tests cover:
- ACTION_TO_EVENT_MAP mapping
- PayloadTranslator static methods
- validate_redux_action function
- ReduxAdapter class

Following HIPAA: No real PHI in test data.
"""

from __future__ import annotations

import pytest
from backend.providers.adapters import (
    ACTION_TO_EVENT_MAP,
    PayloadTranslator,
    ReduxAdapter,
    validate_redux_action,
)
from backend.providers.models import EventType


# ==============================================================================
# Tests for ACTION_TO_EVENT_MAP
# ==============================================================================
class TestActionToEventMap:
    """Tests for Redux action to event type mapping."""

    def test_add_message_mapped(self) -> None:
        """medicalChat/addMessage should map to MESSAGE_RECEIVED."""
        assert ACTION_TO_EVENT_MAP["medicalChat/addMessage"] == EventType.MESSAGE_RECEIVED

    def test_extraction_started_mapped(self) -> None:
        """medicalChat/extractMedicalData/pending should map to EXTRACTION_STARTED."""
        assert (
            ACTION_TO_EVENT_MAP["medicalChat/extractMedicalData/pending"]
            == EventType.EXTRACTION_STARTED
        )

    def test_soap_completed_mapped(self) -> None:
        """soapAnalysisReal/extractionSuccess should map to SOAP_GENERATION_COMPLETED."""
        assert (
            ACTION_TO_EVENT_MAP["soapAnalysisReal/extractionSuccess"]
            == EventType.SOAP_GENERATION_COMPLETED
        )

    def test_llm_events_mapped(self) -> None:
        """LLM decision events should be mapped."""
        assert ACTION_TO_EVENT_MAP["decisions/startDecision"] == EventType.LLM_CALL_INITIATED
        assert ACTION_TO_EVENT_MAP["decisions/completeDecision"] == EventType.LLM_CALL_COMPLETED
        assert ACTION_TO_EVENT_MAP["decisions/failDecision"] == EventType.LLM_CALL_FAILED

    def test_all_values_are_event_types(self) -> None:
        """All mapped values should be EventType enums."""
        for action, event_type in ACTION_TO_EVENT_MAP.items():
            assert isinstance(event_type, EventType), f"{action} maps to non-EventType"


# ==============================================================================
# Tests for validate_redux_action
# ==============================================================================
class TestValidateReduxAction:
    """Tests for validate_redux_action function."""

    def test_valid_action(self) -> None:
        """Valid action with type should return True."""
        action = {"type": "medicalChat/addMessage", "payload": {"content": "test"}}
        assert validate_redux_action(action) is True

    def test_missing_type(self) -> None:
        """Action without type should return False."""
        action = {"payload": {"content": "test"}}
        assert validate_redux_action(action) is False

    def test_type_not_string(self) -> None:
        """Action with non-string type should return False."""
        action = {"type": 123, "payload": {}}
        assert validate_redux_action(action) is False

    def test_not_a_dict(self) -> None:
        """Non-dict input should return False."""
        assert validate_redux_action("not a dict") is False
        assert validate_redux_action(None) is False
        assert validate_redux_action([]) is False

    def test_empty_dict(self) -> None:
        """Empty dict should return False."""
        assert validate_redux_action({}) is False

    def test_minimal_valid_action(self) -> None:
        """Minimal action with just type should be valid."""
        action = {"type": "any/action"}
        assert validate_redux_action(action) is True


# ==============================================================================
# Tests for PayloadTranslator
# ==============================================================================
class TestPayloadTranslatorAddMessage:
    """Tests for PayloadTranslator.translate_add_message."""

    def test_translates_content(self) -> None:
        """Should extract message content."""
        redux_payload = {"content": "Hello doctor", "type": "user"}
        result = PayloadTranslator.translate_add_message(redux_payload)

        assert result["message_content"] == "Hello doctor"

    def test_translates_role(self) -> None:
        """Should translate type to message_role."""
        redux_payload = {"content": "test", "type": "assistant"}
        result = PayloadTranslator.translate_add_message(redux_payload)

        assert result["message_role"] == "assistant"

    def test_includes_metadata(self) -> None:
        """Should include metadata if present."""
        redux_payload = {
            "content": "test",
            "type": "user",
            "metadata": {"confidence": 0.95},
        }
        result = PayloadTranslator.translate_add_message(redux_payload)

        assert result["metadata"]["confidence"] == 0.95

    def test_missing_metadata_defaults_empty(self) -> None:
        """Missing metadata should default to empty dict."""
        redux_payload = {"content": "test", "type": "user"}
        result = PayloadTranslator.translate_add_message(redux_payload)

        assert result["metadata"] == {}


class TestPayloadTranslatorUpdateMessage:
    """Tests for PayloadTranslator.translate_update_message."""

    def test_translates_message_id(self) -> None:
        """Should extract message ID."""
        redux_payload = {"messageId": "msg-123", "content": "updated"}
        result = PayloadTranslator.translate_update_message(redux_payload)

        assert result["message_id"] == "msg-123"

    def test_translates_updated_content(self) -> None:
        """Should extract updated content."""
        redux_payload = {"messageId": "msg-123", "content": "new content"}
        result = PayloadTranslator.translate_update_message(redux_payload)

        assert result["updated_content"] == "new content"


class TestPayloadTranslatorDeleteMessage:
    """Tests for PayloadTranslator.translate_delete_message."""

    def test_translates_message_id(self) -> None:
        """Should extract message ID for deletion."""
        redux_payload = {"messageId": "msg-456"}
        result = PayloadTranslator.translate_delete_message(redux_payload)

        assert result["message_id"] == "msg-456"


class TestPayloadTranslatorExtractionStarted:
    """Tests for PayloadTranslator.translate_extraction_started."""

    def test_default_iteration(self) -> None:
        """Should default to iteration 1."""
        redux_payload = {"meta": {"arg": {}}}
        result = PayloadTranslator.translate_extraction_started(redux_payload)

        assert result["iteration"] == 1

    def test_counts_messages(self) -> None:
        """Should count context messages."""
        redux_payload = {"meta": {"arg": {"messages": [{"id": 1}, {"id": 2}, {"id": 3}]}}}
        result = PayloadTranslator.translate_extraction_started(redux_payload)

        assert result["context_message_count"] == 3

    def test_detects_previous_extraction(self) -> None:
        """Should detect if previous extraction exists."""
        redux_payload = {"meta": {"arg": {"currentExtraction": {"data": "previous"}}}}
        result = PayloadTranslator.translate_extraction_started(redux_payload)

        assert result["has_previous_extraction"] is True

    def test_no_previous_extraction(self) -> None:
        """Should detect no previous extraction."""
        redux_payload = {"meta": {"arg": {"currentExtraction": None}}}
        result = PayloadTranslator.translate_extraction_started(redux_payload)

        assert result["has_previous_extraction"] is False


# ==============================================================================
# Tests for ReduxAdapter
# ==============================================================================
class TestReduxAdapterInit:
    """Tests for ReduxAdapter initialization."""

    def test_can_instantiate(self) -> None:
        """ReduxAdapter should be instantiable."""
        adapter = ReduxAdapter()
        assert adapter is not None


class TestReduxAdapterTranslate:
    """Tests for ReduxAdapter.translate_action."""

    def test_translates_add_message(self) -> None:
        """Should translate addMessage action to event."""
        adapter = ReduxAdapter()
        redux_action = {
            "type": "medicalChat/addMessage",
            "payload": {"content": "Test message", "type": "user"},
        }

        event = adapter.translate_action(
            redux_action,
            consultation_id="consult-123",
            user_id="user-456",
            session_id="session-789",
        )

        assert event is not None
        assert event.event_type == EventType.MESSAGE_RECEIVED

    def test_invalid_action_raises(self) -> None:
        """Invalid action should raise ValueError."""
        adapter = ReduxAdapter()
        redux_action = {"payload": "no type field"}

        with pytest.raises(ValueError):
            adapter.translate_action(
                redux_action,
                consultation_id="consult-123",
                user_id="user-456",
                session_id="session-789",
            )

    def test_unknown_action_raises(self) -> None:
        """Unknown action type should raise ValueError."""
        adapter = ReduxAdapter()
        redux_action = {"type": "unknown/action", "payload": {}}

        with pytest.raises(ValueError) as exc_info:
            adapter.translate_action(
                redux_action,
                consultation_id="consult-123",
                user_id="user-456",
                session_id="session-789",
            )

        assert "Unknown" in str(exc_info.value) or "not mapped" in str(exc_info.value).lower()

    def test_event_has_correct_metadata(self) -> None:
        """Translated event should have correct metadata."""
        adapter = ReduxAdapter()
        redux_action = {
            "type": "medicalChat/addMessage",
            "payload": {"content": "Test", "type": "user"},
        }

        event = adapter.translate_action(
            redux_action,
            consultation_id="consult-123",
            user_id="user-456",
            session_id="session-789",
        )

        assert event.metadata.user_id == "user-456"
        assert event.metadata.session_id == "session-789"
