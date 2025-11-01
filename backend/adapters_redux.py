from __future__ import annotations

"""
Free Intelligence - Redux to Events Adapter

Translates Redux actions from UI to Free Intelligence domain events.

File: backend/adapters_redux.py
Created: 2025-10-28

Purpose:
  - Bridge between Redux-Claude UI and FI event-sourcing backend
  - Translates Redux action payloads to domain event payloads
  - Maps action types to event types (see MAPPING.json)
  - Validates Redux actions before creating events

Usage:
  from backend.adapters_redux import ReduxAdapter

  adapter = ReduxAdapter()
  event = adapter.translate_action(redux_action, consultation_id, user_id)
  event_store.append_event(consultation_id, event)
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from backend.fi_consult_models import ConsultationEvent, EventMetadata, EventType
from backend.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# REDUX ACTION TO EVENT MAPPING
# ============================================================================

# Mapping from Redux action types to FI event types
# Based on MAPPING.json
ACTION_TO_EVENT_MAP = {
    # Consultation lifecycle
    "medicalChat/addMessage": EventType.MESSAGE_RECEIVED,
    "medicalChat/updateMessage": EventType.MESSAGE_UPDATED,
    "medicalChat/deleteMessage": EventType.MESSAGE_DELETED,
    "medicalChat/clearMessages": EventType.MESSAGES_CLEARED,
    "medicalChat/markMessageAsProcessed": EventType.MESSAGE_PROCESSED,
    "medicalChat/resetSession": EventType.CONSULTATION_RESET,
    # Extraction
    "medicalChat/extractMedicalData/pending": EventType.EXTRACTION_STARTED,
    "medicalChat/extractMedicalData/fulfilled": EventType.EXTRACTION_COMPLETED,
    "medicalChat/extractMedicalData/rejected": EventType.EXTRACTION_FAILED,
    "medicalChat/incrementIteration": EventType.EXTRACTION_ITERATION_INCREMENTED,
    "medicalChat/completeExtraction": EventType.EXTRACTION_PROCESS_COMPLETED,
    # WIP Data
    "medicalChat/updateDemographics": EventType.DEMOGRAPHICS_UPDATED,
    "medicalChat/updateSymptoms": EventType.SYMPTOMS_UPDATED,
    "medicalChat/updateContext": EventType.CONTEXT_UPDATED,
    "medicalChat/updateCompleteness": EventType.COMPLETENESS_CALCULATED,
    # SOAP
    "soapAnalysisReal/startSOAPExtraction": EventType.SOAP_GENERATION_STARTED,
    "soapAnalysisReal/updateSOAPSection": EventType.SOAP_SECTION_COMPLETED,
    "soapAnalysisReal/extractionSuccess": EventType.SOAP_GENERATION_COMPLETED,
    "soapAnalysisReal/extractionError": EventType.SOAP_GENERATION_FAILED,
    "soapAnalysisReal/completeAnalysis": EventType.CONSULTATION_COMMITTED,
    # Cognitive/Urgency
    "cognitive/addCognitiveEvent": EventType.CRITICAL_PATTERN_DETECTED,
    "cognitive/updateSystemHealth": EventType.URGENCY_CLASSIFIED,
    # Decisions (LLM)
    "decisions/startDecision": EventType.LLM_CALL_INITIATED,
    "decisions/completeDecision": EventType.LLM_CALL_COMPLETED,
    "decisions/failDecision": EventType.LLM_CALL_FAILED,
    # Audit
    "decisions/addAuditEntries": EventType.AUDIT_ENTRY_CREATED,
    # System
    "medicalChat/setCoreLoading": EventType.CORE_STATE_CHANGED,
    "medicalChat/setCoreError": EventType.CORE_ERROR_OCCURRED,
}


# ============================================================================
# PAYLOAD TRANSLATORS
# ============================================================================


class PayloadTranslator:
    """Translates Redux action payloads to FI event payloads."""

    @staticmethod
    def translate_add_message(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/addMessage payload."""
        return {
            "message_content": redux_payload.get("content"),
            "message_role": redux_payload.get("type"),  # 'user' or 'assistant'
            "metadata": redux_payload.get("metadata", {}),
        }

    @staticmethod
    def translate_update_message(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/updateMessage payload."""
        return {
            "message_id": redux_payload.get("messageId"),
            "updated_content": redux_payload.get("content"),
        }

    @staticmethod
    def translate_delete_message(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/deleteMessage payload."""
        return {"message_id": redux_payload.get("messageId")}

    @staticmethod
    def translate_extraction_started(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/extractMedicalData/pending payload."""
        meta_arg = redux_payload.get("meta", {}).get("arg", {})
        return {
            "iteration": 1,  # Assume first iteration if not specified
            "context_message_count": len(meta_arg.get("messages", [])),
            "has_previous_extraction": meta_arg.get("currentExtraction") is not None,
        }

    @staticmethod
    def translate_extraction_completed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/extractMedicalData/fulfilled payload."""
        return {
            "iteration": redux_payload.get("iteration", 1),
            "completeness": redux_payload.get("completenessPercentage", 0),
            "nom_compliance": redux_payload.get("nomCompliance", 0),
            "missing_fields": redux_payload.get("missingFields", []),
            "extraction_data": redux_payload.get("extraction", {}),
        }

    @staticmethod
    def translate_extraction_failed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/extractMedicalData/rejected payload."""
        return {
            "iteration": redux_payload.get("iteration", 1),
            "error_message": redux_payload.get("error", "Unknown error"),
            "error_type": redux_payload.get("errorType", "extraction_error"),
        }

    @staticmethod
    def translate_demographics(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/updateDemographics payload."""
        return {
            "age": redux_payload.get("age"),
            "gender": redux_payload.get("gender"),
            "weight": redux_payload.get("weight"),
            "height": redux_payload.get("height"),
            "occupation": redux_payload.get("occupation"),
        }

    @staticmethod
    def translate_symptoms(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/updateSymptoms payload."""
        return {
            "primary_symptoms": redux_payload.get("primarySymptoms", []),
            "secondary_symptoms": redux_payload.get("secondarySymptoms"),
            "duration": redux_payload.get("duration"),
            "severity": redux_payload.get("severity"),
            "location": redux_payload.get("location"),
            "quality": redux_payload.get("quality"),
            "aggravating_factors": redux_payload.get("aggravatingFactors"),
            "relieving_factors": redux_payload.get("relievingFactors"),
        }

    @staticmethod
    def translate_context(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/updateContext payload."""
        return {
            "past_medical_history": redux_payload.get("pastMedicalHistory"),
            "family_history": redux_payload.get("familyHistory"),
            "medications": redux_payload.get("medications"),
            "allergies": redux_payload.get("allergies"),
            "surgeries": redux_payload.get("surgeries"),
        }

    @staticmethod
    def translate_completeness(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate medicalChat/updateCompleteness payload."""
        return {
            "completeness_percentage": redux_payload.get("percentage", 0),
            "missing_critical_fields": redux_payload.get("missingCriticalFields", []),
        }

    @staticmethod
    def translate_soap_section(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate soapAnalysisReal/updateSOAPSection payload."""
        return {
            "section_name": redux_payload.get("section"),
            "section_content": redux_payload.get("content"),
            "confidence": redux_payload.get("confidence", 0.0),
        }

    @staticmethod
    def translate_soap_completed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate soapAnalysisReal/extractionSuccess payload."""
        return {
            "soap_data": redux_payload.get("analysis", {}),
            "quality_score": redux_payload.get("quality", 0.0),
            "ready_for_commit": True,
        }

    @staticmethod
    def translate_soap_failed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate soapAnalysisReal/extractionError payload."""
        return {
            "error_message": redux_payload.get("error", "Unknown error"),
            "partial_soap": redux_payload.get("partialSoap"),
        }

    @staticmethod
    def translate_critical_pattern(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate cognitive/addCognitiveEvent payload."""
        data = redux_payload.get("data", {})
        return {
            "pattern_name": redux_payload.get("eventType", "unknown"),
            "gravity_score": data.get("gravityScore", 5),
            "widow_maker_alert": data.get("widowMakerAlert", False),
            "symptoms_matched": data.get("symptomsMatched", []),
            "critical_differentials": data.get("criticalDifferentials", []),
            "time_to_action": data.get("timeToAction", "unknown"),
        }

    @staticmethod
    def translate_urgency(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate cognitive/updateSystemHealth payload."""
        metrics = redux_payload.get("metrics", {})
        return {
            "urgency_level": redux_payload.get("health", "medium"),
            "gravity_score": metrics.get("gravityScore", 5),
            "time_to_action": metrics.get("timeToAction", "unknown"),
            "identified_patterns": metrics.get("identifiedPatterns", []),
            "risk_factors": metrics.get("riskFactors", []),
        }

    @staticmethod
    def translate_llm_initiated(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate decisions/startDecision payload."""
        return {
            "decision_id": redux_payload.get("id"),
            "llm_provider": redux_payload.get("provider", "claude"),
            "query_text": redux_payload.get("query", ""),
            "agent_name": redux_payload.get("agentName"),
        }

    @staticmethod
    def translate_llm_completed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate decisions/completeDecision payload."""
        return {
            "decision_id": redux_payload.get("id"),
            "llm_provider": redux_payload.get("provider", "claude"),
            "decision_result": redux_payload.get("decision"),
            "confidence": redux_payload.get("confidence", 0.0),
            "latency_ms": redux_payload.get("latency", 0),
            "tokens_used": redux_payload.get("tokensUsed"),
        }

    @staticmethod
    def translate_llm_failed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate decisions/failDecision payload."""
        return {
            "decision_id": redux_payload.get("id"),
            "error_message": redux_payload.get("error", "Unknown error"),
            "retry_count": redux_payload.get("retryCount", 0),
        }

    @staticmethod
    def translate_audit_entries(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate decisions/addAuditEntries payload."""
        # Redux payload is array of audit entries
        if isinstance(redux_payload, list):
            return {"audit_entries": redux_payload}
        return {"audit_entries": [redux_payload]}

    @staticmethod
    def translate_consultation_committed(redux_payload: dict[str, Any]) -> dict[str, Any]:
        """Translate soapAnalysisReal/completeAnalysis payload."""
        from backend.fi_event_store import calculate_sha256

        soap_data = redux_payload.get("finalAnalysis", {})
        commit_hash = calculate_sha256(soap_data)

        return {
            "soap_data": soap_data,
            "committed_by": "user_id",  # Should come from session
            "commit_hash": commit_hash,
            "quality_score": soap_data.get("quality_score", 0.0),
            "completeness": soap_data.get("completeness", 0.0),
            "nom_compliance": soap_data.get("nom_compliance", 0.0),
        }


# ============================================================================
# REDUX ADAPTER
# ============================================================================


class ReduxAdapter:
    """
    Adapter to translate Redux actions to FI domain events.
    """

    def __init__(self):
        """Initialize adapter."""
        self.translator = PayloadTranslator()
        logger.info("REDUX_ADAPTER_INITIALIZED")

    def translate_action(
        self,
        redux_action: dict[str, Any],
        consultation_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> ConsultationEvent:
        """
        Translate Redux action to FI domain event.

        Args:
            redux_action: Redux action dict with 'type' and 'payload'
            consultation_id: Consultation UUID
            user_id: User ID
            session_id: Session ID (optional, will generate if not provided)

        Returns:
            ConsultationEvent ready for append to event store

        Raises:
            ValueError: If action type not recognized
        """
        action_type = redux_action.get("type")
        redux_payload = redux_action.get("payload", {})

        # Map action type to event type
        if action_type not in ACTION_TO_EVENT_MAP:
            logger.warning("UNKNOWN_REDUX_ACTION", action_type=action_type)
            raise ValueError(f"Unknown Redux action type: {action_type}")

        event_type = ACTION_TO_EVENT_MAP[action_type]

        # Translate payload
        event_payload = self._translate_payload(action_type, redux_payload)

        # Generate session_id if not provided
        if session_id is None:
            session_id = str(uuid4())

        # Create event
        event = ConsultationEvent(
            event_id=str(uuid4()),
            consultation_id=consultation_id,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            payload=event_payload,
            metadata=EventMetadata(
                user_id=user_id,
                session_id=session_id,
                source="redux_adapter",
                timezone="America/Mexico_City",
            ),
        )

        logger.info(
            "REDUX_ACTION_TRANSLATED",
            redux_action_type=action_type,
            event_type=event_type.value,
            event_id=event.event_id,
        )

        return event

    def _translate_payload(self, action_type: str, redux_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Translate Redux payload to event payload.

        Args:
            action_type: Redux action type
            redux_payload: Redux payload dict

        Returns:
            Translated event payload dict
        """
        # Map action types to translator methods
        translator_map = {
            "medicalChat/addMessage": self.translator.translate_add_message,
            "medicalChat/updateMessage": self.translator.translate_update_message,
            "medicalChat/deleteMessage": self.translator.translate_delete_message,
            "medicalChat/extractMedicalData/pending": self.translator.translate_extraction_started,
            "medicalChat/extractMedicalData/fulfilled": self.translator.translate_extraction_completed,
            "medicalChat/extractMedicalData/rejected": self.translator.translate_extraction_failed,
            "medicalChat/updateDemographics": self.translator.translate_demographics,
            "medicalChat/updateSymptoms": self.translator.translate_symptoms,
            "medicalChat/updateContext": self.translator.translate_context,
            "medicalChat/updateCompleteness": self.translator.translate_completeness,
            "soapAnalysisReal/updateSOAPSection": self.translator.translate_soap_section,
            "soapAnalysisReal/extractionSuccess": self.translator.translate_soap_completed,
            "soapAnalysisReal/extractionError": self.translator.translate_soap_failed,
            "soapAnalysisReal/completeAnalysis": self.translator.translate_consultation_committed,
            "cognitive/addCognitiveEvent": self.translator.translate_critical_pattern,
            "cognitive/updateSystemHealth": self.translator.translate_urgency,
            "decisions/startDecision": self.translator.translate_llm_initiated,
            "decisions/completeDecision": self.translator.translate_llm_completed,
            "decisions/failDecision": self.translator.translate_llm_failed,
            "decisions/addAuditEntries": self.translator.translate_audit_entries,
        }

        # Get translator method
        translator_method = translator_map.get(action_type)

        if translator_method:
            return translator_method(redux_payload)

        # Default: pass through payload
        logger.warning("NO_PAYLOAD_TRANSLATOR", action_type=action_type, using_default=True)
        return redux_payload


# ============================================================================
# BATCH TRANSLATOR
# ============================================================================


class BatchReduxAdapter:
    """
    Batch adapter for translating multiple Redux actions at once.
    Useful for replaying Redux action history.
    """

    def __init__(self):
        """Initialize batch adapter."""
        self.adapter = ReduxAdapter()

    def translate_batch(
        self,
        redux_actions: list[dict[str, Any]],
        consultation_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> list[ConsultationEvent]:
        """
        Translate batch of Redux actions to events.

        Args:
            redux_actions: List of Redux action dicts
            consultation_id: Consultation UUID
            user_id: User ID
            session_id: Session ID (optional)

        Returns:
            List of ConsultationEvents
        """
        events = []

        for redux_action in redux_actions:
            try:
                event = self.adapter.translate_action(
                    redux_action, consultation_id, user_id, session_id
                )
                events.append(event)
            except ValueError as e:
                logger.warning(
                    "BATCH_TRANSLATION_SKIPPED", action_type=redux_action.get("type"), error=str(e)
                )

        logger.info(
            "BATCH_TRANSLATION_COMPLETED",
            total_actions=len(redux_actions),
            successful_events=len(events),
        )

        return events


# ============================================================================
# VALIDATION
# ============================================================================


def validate_redux_action(redux_action: dict[str, Any]) -> bool:
    """
    Validate Redux action structure.

    Args:
        redux_action: Redux action dict

    Returns:
        True if valid, False otherwise
    """
    return (
        isinstance(redux_action, dict)
        and "type" in redux_action
        and isinstance(redux_action["type"], str)
    )


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI interface for testing adapter."""
    import json

    # Example Redux action
    redux_action = {
        "type": "medicalChat/addMessage",
        "payload": {
            "content": "Hello, I have chest pain",
            "type": "user",
            "metadata": {"confidence": 0.95},
        },
    }

    adapter = ReduxAdapter()

    try:
        event = adapter.translate_action(
            redux_action,
            consultation_id="test-consultation-123",
            user_id="test-user",
            session_id="test-session",
        )

        print("Redux Action:")
        print(json.dumps(redux_action, indent=2))
        print("\nTranslated Event:")
        print(event.model_dump_json(indent=2))

    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
