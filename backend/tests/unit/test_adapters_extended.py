"""Extended unit tests for adapters module.

Tests for Redux to Events translation functionality.
"""

from __future__ import annotations

from typing import Any

import pytest

# ==============================================================================
# ACTION TO EVENT MAP TESTS
# ==============================================================================


class TestActionToEventMap:
    """Tests for ACTION_TO_EVENT_MAP."""

    def test_action_map_contains_message_actions(self) -> None:
        """Test action map contains message-related actions."""
        from backend.providers.adapters import ACTION_TO_EVENT_MAP
        from backend.providers.models import EventType

        assert ACTION_TO_EVENT_MAP["medicalChat/addMessage"] == EventType.MESSAGE_RECEIVED
        assert ACTION_TO_EVENT_MAP["medicalChat/updateMessage"] == EventType.MESSAGE_UPDATED
        assert ACTION_TO_EVENT_MAP["medicalChat/deleteMessage"] == EventType.MESSAGE_DELETED

    def test_action_map_contains_extraction_actions(self) -> None:
        """Test action map contains extraction actions."""
        from backend.providers.adapters import ACTION_TO_EVENT_MAP
        from backend.providers.models import EventType

        assert ACTION_TO_EVENT_MAP["medicalChat/extractMedicalData/pending"] == EventType.EXTRACTION_STARTED
        assert ACTION_TO_EVENT_MAP["medicalChat/extractMedicalData/fulfilled"] == EventType.EXTRACTION_COMPLETED
        assert ACTION_TO_EVENT_MAP["medicalChat/extractMedicalData/rejected"] == EventType.EXTRACTION_FAILED

    def test_action_map_contains_soap_actions(self) -> None:
        """Test action map contains SOAP-related actions."""
        from backend.providers.adapters import ACTION_TO_EVENT_MAP
        from backend.providers.models import EventType

        assert ACTION_TO_EVENT_MAP["soapAnalysisReal/startSOAPExtraction"] == EventType.SOAP_GENERATION_STARTED
        assert ACTION_TO_EVENT_MAP["soapAnalysisReal/updateSOAPSection"] == EventType.SOAP_SECTION_COMPLETED
        assert ACTION_TO_EVENT_MAP["soapAnalysisReal/extractionSuccess"] == EventType.SOAP_GENERATION_COMPLETED


# ==============================================================================
# PAYLOAD TRANSLATOR TESTS
# ==============================================================================


class TestPayloadTranslator:
    """Tests for PayloadTranslator class."""

    def test_translate_add_message(self) -> None:
        """Test translate_add_message translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "content": "Hello doctor",
            "type": "user",
            "metadata": {"timestamp": "2026-01-18T12:00:00Z"},
        }

        result = PayloadTranslator.translate_add_message(redux_payload)

        assert result["message_content"] == "Hello doctor"
        assert result["message_role"] == "user"
        assert result["metadata"]["timestamp"] == "2026-01-18T12:00:00Z"

    def test_translate_add_message_minimal(self) -> None:
        """Test translate_add_message with minimal payload."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {"content": "Test"}

        result = PayloadTranslator.translate_add_message(redux_payload)

        assert result["message_content"] == "Test"
        assert result["message_role"] is None
        assert result["metadata"] == {}

    def test_translate_update_message(self) -> None:
        """Test translate_update_message translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "messageId": "msg-123",
            "content": "Updated content",
        }

        result = PayloadTranslator.translate_update_message(redux_payload)

        assert result["message_id"] == "msg-123"
        assert result["updated_content"] == "Updated content"

    def test_translate_delete_message(self) -> None:
        """Test translate_delete_message translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {"messageId": "msg-456"}

        result = PayloadTranslator.translate_delete_message(redux_payload)

        assert result["message_id"] == "msg-456"

    def test_translate_extraction_started(self) -> None:
        """Test translate_extraction_started translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "meta": {
                "arg": {
                    "messages": [{"id": 1}, {"id": 2}],
                    "currentExtraction": {"field": "value"},
                }
            }
        }

        result = PayloadTranslator.translate_extraction_started(redux_payload)

        assert result["iteration"] == 1
        assert result["context_message_count"] == 2
        assert result["has_previous_extraction"] is True

    def test_translate_extraction_started_no_previous(self) -> None:
        """Test translate_extraction_started without previous extraction."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "meta": {
                "arg": {
                    "messages": [],
                    "currentExtraction": None,
                }
            }
        }

        result = PayloadTranslator.translate_extraction_started(redux_payload)

        assert result["context_message_count"] == 0
        assert result["has_previous_extraction"] is False

    def test_translate_extraction_completed(self) -> None:
        """Test translate_extraction_completed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "iteration": 3,
            "completenessPercentage": 85,
            "nomCompliance": 90,
            "missingFields": ["allergies", "medications"],
            "extraction": {"symptoms": "headache"},
        }

        result = PayloadTranslator.translate_extraction_completed(redux_payload)

        assert result["iteration"] == 3
        assert result["completeness"] == 85
        assert result["nom_compliance"] == 90
        assert result["missing_fields"] == ["allergies", "medications"]
        assert result["extraction_data"] == {"symptoms": "headache"}

    def test_translate_extraction_completed_defaults(self) -> None:
        """Test translate_extraction_completed with defaults."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {}

        result = PayloadTranslator.translate_extraction_completed(redux_payload)

        assert result["iteration"] == 1
        assert result["completeness"] == 0
        assert result["nom_compliance"] == 0
        assert result["missing_fields"] == []
        assert result["extraction_data"] == {}

    def test_translate_extraction_failed(self) -> None:
        """Test translate_extraction_failed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "iteration": 2,
            "error": "LLM timeout",
            "errorType": "timeout_error",
        }

        result = PayloadTranslator.translate_extraction_failed(redux_payload)

        assert result["iteration"] == 2
        assert result["error_message"] == "LLM timeout"
        assert result["error_type"] == "timeout_error"

    def test_translate_extraction_failed_defaults(self) -> None:
        """Test translate_extraction_failed with defaults."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {}

        result = PayloadTranslator.translate_extraction_failed(redux_payload)

        assert result["iteration"] == 1
        assert result["error_message"] == "Unknown error"
        assert result["error_type"] == "extraction_error"

    def test_translate_demographics(self) -> None:
        """Test translate_demographics translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "age": 35,
            "gender": "M",
            "weight": 75.5,
            "height": 180,
            "occupation": "Engineer",
        }

        result = PayloadTranslator.translate_demographics(redux_payload)

        assert result["age"] == 35
        assert result["gender"] == "M"
        assert result["weight"] == 75.5
        assert result["height"] == 180
        assert result["occupation"] == "Engineer"

    def test_translate_symptoms(self) -> None:
        """Test translate_symptoms translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "primarySymptoms": ["headache", "fever"],
            "secondarySymptoms": "fatigue",
            "duration": "3 days",
            "severity": "moderate",
            "location": "frontal",
            "quality": "throbbing",
            "aggravatingFactors": "light",
            "relievingFactors": "rest",
        }

        result = PayloadTranslator.translate_symptoms(redux_payload)

        assert result["primary_symptoms"] == ["headache", "fever"]
        assert result["secondary_symptoms"] == "fatigue"
        assert result["duration"] == "3 days"
        assert result["severity"] == "moderate"
        assert result["location"] == "frontal"
        assert result["quality"] == "throbbing"
        assert result["aggravating_factors"] == "light"
        assert result["relieving_factors"] == "rest"

    def test_translate_context(self) -> None:
        """Test translate_context translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "pastMedicalHistory": "Diabetes",
            "familyHistory": "Heart disease",
            "medications": ["Metformin"],
            "allergies": ["Penicillin"],
            "surgeries": ["Appendectomy"],
        }

        result = PayloadTranslator.translate_context(redux_payload)

        assert result["past_medical_history"] == "Diabetes"
        assert result["family_history"] == "Heart disease"
        assert result["medications"] == ["Metformin"]
        assert result["allergies"] == ["Penicillin"]
        assert result["surgeries"] == ["Appendectomy"]

    def test_translate_completeness(self) -> None:
        """Test translate_completeness translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "percentage": 75,
            "missingCriticalFields": ["allergies", "medications"],
        }

        result = PayloadTranslator.translate_completeness(redux_payload)

        assert result["completeness_percentage"] == 75
        assert result["missing_critical_fields"] == ["allergies", "medications"]

    def test_translate_completeness_defaults(self) -> None:
        """Test translate_completeness with defaults."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {}

        result = PayloadTranslator.translate_completeness(redux_payload)

        assert result["completeness_percentage"] == 0
        assert result["missing_critical_fields"] == []

    def test_translate_soap_section(self) -> None:
        """Test translate_soap_section translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "section": "subjective",
            "content": "Patient reports headache for 3 days",
            "confidence": 0.95,
        }

        result = PayloadTranslator.translate_soap_section(redux_payload)

        assert result["section_name"] == "subjective"
        assert result["section_content"] == "Patient reports headache for 3 days"
        assert result["confidence"] == 0.95

    def test_translate_soap_section_defaults(self) -> None:
        """Test translate_soap_section with defaults."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {"section": "objective"}

        result = PayloadTranslator.translate_soap_section(redux_payload)

        assert result["section_name"] == "objective"
        assert result["section_content"] is None
        assert result["confidence"] == 0.0

    def test_translate_soap_completed(self) -> None:
        """Test translate_soap_completed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "analysis": {"subjective": "...", "objective": "..."},
            "quality": 0.88,
        }

        result = PayloadTranslator.translate_soap_completed(redux_payload)

        assert result["soap_data"] == {"subjective": "...", "objective": "..."}
        assert result["quality_score"] == 0.88


# ==============================================================================
# REDUX ADAPTER TESTS
# ==============================================================================


class TestReduxAdapter:
    """Tests for ReduxAdapter class."""

    def test_redux_adapter_translate_add_message(self) -> None:
        """Test ReduxAdapter translates addMessage action."""
        from backend.providers.adapters import ReduxAdapter
        from backend.providers.models import EventType

        adapter = ReduxAdapter()

        redux_action = {
            "type": "medicalChat/addMessage",
            "payload": {
                "content": "Hello doctor",
                "type": "user",
            },
        }

        event = adapter.translate_action(
            redux_action=redux_action,
            consultation_id="consul-123",
            user_id="user-456",
        )

        assert event.event_type == EventType.MESSAGE_RECEIVED
        assert event.consultation_id == "consul-123"
        assert event.payload["message_content"] == "Hello doctor"
        assert event.payload["message_role"] == "user"

    def test_redux_adapter_translate_extraction_started(self) -> None:
        """Test ReduxAdapter translates extraction started action."""
        from backend.providers.adapters import ReduxAdapter
        from backend.providers.models import EventType

        adapter = ReduxAdapter()

        # For extraction started, the meta.arg is in a nested payload
        redux_action = {
            "type": "medicalChat/extractMedicalData/pending",
            "payload": {
                "meta": {
                    "arg": {
                        "messages": [{"id": 1}],
                        "currentExtraction": None,
                    }
                }
            },
        }

        event = adapter.translate_action(
            redux_action=redux_action,
            consultation_id="consul-789",
            user_id="user-123",
        )

        assert event.event_type == EventType.EXTRACTION_STARTED

    def test_redux_adapter_unknown_action_raises(self) -> None:
        """Test ReduxAdapter raises for unknown action."""
        from backend.providers.adapters import ReduxAdapter

        adapter = ReduxAdapter()

        redux_action = {
            "type": "unknown/action",
            "payload": {},
        }

        with pytest.raises(ValueError, match="Unknown Redux action"):
            adapter.translate_action(
                redux_action=redux_action,
                consultation_id="consul-123",
                user_id="user-456",
            )

    def test_redux_adapter_event_has_metadata(self) -> None:
        """Test translated events have proper metadata."""
        from backend.providers.adapters import ReduxAdapter

        adapter = ReduxAdapter()

        redux_action = {
            "type": "medicalChat/addMessage",
            "payload": {"content": "Test"},
        }

        event = adapter.translate_action(
            redux_action=redux_action,
            consultation_id="consul-123",
            user_id="user-456",
        )

        # Event should have metadata
        assert event.metadata is not None
        # Metadata has timestamp and source
        assert hasattr(event.metadata, "timestamp") or hasattr(event.metadata, "source")

    def test_redux_adapter_event_has_unique_id(self) -> None:
        """Test translated events have unique IDs."""
        from backend.providers.adapters import ReduxAdapter

        adapter = ReduxAdapter()

        redux_action = {
            "type": "medicalChat/addMessage",
            "payload": {"content": "Test"},
        }

        event1 = adapter.translate_action(
            redux_action=redux_action,
            consultation_id="consul-123",
            user_id="user-456",
        )

        event2 = adapter.translate_action(
            redux_action=redux_action,
            consultation_id="consul-123",
            user_id="user-456",
        )

        # Each event should have a unique ID
        assert event1.event_id != event2.event_id


# ==============================================================================
# BATCH REDUX ADAPTER TESTS
# ==============================================================================


class TestBatchReduxAdapter:
    """Tests for BatchReduxAdapter class."""

    def test_batch_adapter_creation(self) -> None:
        """Test batch adapter can be created."""
        from backend.providers.adapters import BatchReduxAdapter

        adapter = BatchReduxAdapter()
        assert adapter is not None
        assert hasattr(adapter, "adapter")
        assert hasattr(adapter, "translate_batch")

    def test_batch_translate_empty_list(self) -> None:
        """Test translating empty list returns empty list."""
        from backend.providers.adapters import BatchReduxAdapter

        adapter = BatchReduxAdapter()
        events = adapter.translate_batch(
            redux_actions=[],
            consultation_id="consul-123",
            user_id="user-456",
        )

        assert events == []

    def test_batch_translate_single_action(self) -> None:
        """Test translating single action."""
        from backend.providers.adapters import BatchReduxAdapter

        adapter = BatchReduxAdapter()

        actions = [
            {
                "type": "medicalChat/addMessage",
                "payload": {"content": "Test message"},
            }
        ]

        events = adapter.translate_batch(
            redux_actions=actions,
            consultation_id="consul-123",
            user_id="user-456",
        )

        assert len(events) == 1

    def test_batch_translate_multiple_actions(self) -> None:
        """Test translating multiple actions."""
        from backend.providers.adapters import BatchReduxAdapter

        adapter = BatchReduxAdapter()

        actions = [
            {"type": "medicalChat/addMessage", "payload": {"content": "First"}},
            {"type": "medicalChat/addMessage", "payload": {"content": "Second"}},
            {"type": "medicalChat/updateMessage", "payload": {"id": "msg-1", "content": "Updated"}},
        ]

        events = adapter.translate_batch(
            redux_actions=actions,
            consultation_id="consul-123",
            user_id="user-456",
            session_id="session-789",
        )

        assert len(events) == 3

    def test_batch_translate_skips_invalid_actions(self) -> None:
        """Test batch translation skips invalid actions."""
        from backend.providers.adapters import BatchReduxAdapter

        adapter = BatchReduxAdapter()

        actions = [
            {"type": "medicalChat/addMessage", "payload": {"content": "Valid"}},
            {"type": "unknown/invalidAction", "payload": {}},  # Will cause error
            {"type": "medicalChat/addMessage", "payload": {"content": "Also Valid"}},
        ]

        events = adapter.translate_batch(
            redux_actions=actions,
            consultation_id="consul-123",
            user_id="user-456",
        )

        # Should have at least the valid actions
        assert len(events) >= 2


# ==============================================================================
# VALIDATE REDUX ACTION TESTS
# ==============================================================================


class TestValidateReduxAction:
    """Tests for validate_redux_action function."""

    def test_valid_action_returns_true(self) -> None:
        """Test valid action returns True."""
        from backend.providers.adapters import validate_redux_action

        action = {"type": "test/action", "payload": {}}
        assert validate_redux_action(action) is True

    def test_action_without_type_returns_false(self) -> None:
        """Test action without type returns False."""
        from backend.providers.adapters import validate_redux_action

        action = {"payload": {}}
        assert validate_redux_action(action) is False

    def test_non_dict_action_returns_false(self) -> None:
        """Test non-dict action returns False."""
        from backend.providers.adapters import validate_redux_action

        assert validate_redux_action("not a dict") is False
        assert validate_redux_action(None) is False  # type: ignore
        assert validate_redux_action([]) is False

    def test_action_with_non_string_type_returns_false(self) -> None:
        """Test action with non-string type returns False."""
        from backend.providers.adapters import validate_redux_action

        action = {"type": 123, "payload": {}}
        assert validate_redux_action(action) is False


# ==============================================================================
# ADDITIONAL PAYLOAD TRANSLATOR TESTS
# ==============================================================================


class TestPayloadTranslatorAdditional:
    """Additional tests for PayloadTranslator methods."""

    def test_translate_soap_failed(self) -> None:
        """Test translate_soap_failed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "error": "Network timeout",
            "partialSoap": {"subjective": "Partial data"},
        }

        result = PayloadTranslator.translate_soap_failed(redux_payload)

        assert result["error_message"] == "Network timeout"
        assert result["partial_soap"]["subjective"] == "Partial data"

    def test_translate_soap_failed_defaults(self) -> None:
        """Test translate_soap_failed with missing fields."""
        from backend.providers.adapters import PayloadTranslator

        result = PayloadTranslator.translate_soap_failed({})

        assert result["error_message"] == "Unknown error"
        assert result["partial_soap"] is None

    def test_translate_critical_pattern(self) -> None:
        """Test translate_critical_pattern translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "eventType": "chest_pain",
            "data": {
                "gravityScore": 8,
                "widowMakerAlert": True,
                "symptomsMatched": ["chest pain", "shortness of breath"],
                "criticalDifferentials": ["MI", "PE"],
                "timeToAction": "immediate",
            },
        }

        result = PayloadTranslator.translate_critical_pattern(redux_payload)

        assert result["pattern_name"] == "chest_pain"
        assert result["gravity_score"] == 8
        assert result["widow_maker_alert"] is True
        assert len(result["symptoms_matched"]) == 2
        assert "MI" in result["critical_differentials"]

    def test_translate_urgency(self) -> None:
        """Test translate_urgency translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "health": "high",
            "metrics": {
                "gravityScore": 7,
                "timeToAction": "30 minutes",
                "identifiedPatterns": ["fever"],
                "riskFactors": ["diabetes"],
            },
        }

        result = PayloadTranslator.translate_urgency(redux_payload)

        assert result["urgency_level"] == "high"
        assert result["gravity_score"] == 7
        assert result["time_to_action"] == "30 minutes"

    def test_translate_llm_initiated(self) -> None:
        """Test translate_llm_initiated translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "id": "decision-123",
            "provider": "claude",
            "query": "Analyze symptoms",
            "agentName": "diagnostic_agent",
        }

        result = PayloadTranslator.translate_llm_initiated(redux_payload)

        assert result["decision_id"] == "decision-123"
        assert result["llm_provider"] == "claude"
        assert result["query_text"] == "Analyze symptoms"
        assert result["agent_name"] == "diagnostic_agent"

    def test_translate_llm_completed(self) -> None:
        """Test translate_llm_completed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "id": "decision-456",
            "provider": "ollama",
            "decision": "Recommend chest X-ray",
            "confidence": 0.92,
            "latency": 1500,
            "tokensUsed": 250,
        }

        result = PayloadTranslator.translate_llm_completed(redux_payload)

        assert result["decision_id"] == "decision-456"
        assert result["llm_provider"] == "ollama"
        assert result["decision_result"] == "Recommend chest X-ray"
        assert result["confidence"] == 0.92
        assert result["latency_ms"] == 1500
        assert result["tokens_used"] == 250

    def test_translate_llm_failed(self) -> None:
        """Test translate_llm_failed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "id": "decision-789",
            "error": "API timeout",
            "retryCount": 3,
        }

        result = PayloadTranslator.translate_llm_failed(redux_payload)

        assert result["decision_id"] == "decision-789"
        assert result["error_message"] == "API timeout"
        assert result["retry_count"] == 3

    def test_translate_audit_entries_list(self) -> None:
        """Test translate_audit_entries with list payload."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = [
            {"action": "view", "timestamp": "2025-01-01"},
            {"action": "edit", "timestamp": "2025-01-02"},
        ]

        result = PayloadTranslator.translate_audit_entries(redux_payload)

        assert len(result["audit_entries"]) == 2

    def test_translate_audit_entries_single(self) -> None:
        """Test translate_audit_entries with single entry."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {"action": "view", "timestamp": "2025-01-01"}

        result = PayloadTranslator.translate_audit_entries(redux_payload)

        assert len(result["audit_entries"]) == 1

    def test_translate_consultation_committed(self) -> None:
        """Test translate_consultation_committed translation."""
        from backend.providers.adapters import PayloadTranslator

        redux_payload = {
            "finalAnalysis": {
                "subjective": "Patient reports headache",
                "objective": "BP 120/80",
                "assessment": "Tension headache",
                "plan": "OTC pain relief",
                "quality_score": 0.85,
                "completeness": 0.9,
                "nom_compliance": 0.95,
            }
        }

        result = PayloadTranslator.translate_consultation_committed(redux_payload)

        assert result["soap_data"]["subjective"] == "Patient reports headache"
        assert result["quality_score"] == 0.85
        assert result["completeness"] == 0.9
        assert result["nom_compliance"] == 0.95
        assert result["commit_hash"] is not None  # SHA256 generated
