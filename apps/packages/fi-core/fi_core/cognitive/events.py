"""Redux → domain-event mapping for event-sourcing.

Ported faithfully from the Redux-Claude flow (`backend/providers/adapters.py`
+ `models.py`, spec in `docs/MAPPING.json`). Translates Redux actions
dispatched by a UI into immutable domain events suitable for an event store.

Zero-dep: the backend originals used Pydantic + a project SHA helper; here the
event envelope is plain `dataclasses` and the audit hash uses stdlib `hashlib`.

    adapter = ReduxEventAdapter()
    event = adapter.translate_action(
        {"type": "medicalChat/addMessage",
         "payload": {"content": "chest pain", "type": "user"}},
        consultation_id="c-123", user_id="u-1",
    )
    print(event.event_type, event.payload)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class EventType(str, Enum):
    """Domain event types (FLOW.md event vocabulary / models.py EventType)."""

    # Consultation lifecycle
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    MESSAGE_UPDATED = "MESSAGE_UPDATED"
    MESSAGE_DELETED = "MESSAGE_DELETED"
    MESSAGE_PROCESSED = "MESSAGE_PROCESSED"
    MESSAGES_CLEARED = "MESSAGES_CLEARED"
    CONSULTATION_RESET = "CONSULTATION_RESET"
    CONSULTATION_COMMITTED = "CONSULTATION_COMMITTED"
    # Extraction
    EXTRACTION_STARTED = "EXTRACTION_STARTED"
    EXTRACTION_COMPLETED = "EXTRACTION_COMPLETED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_ITERATION_INCREMENTED = "EXTRACTION_ITERATION_INCREMENTED"
    EXTRACTION_PROCESS_COMPLETED = "EXTRACTION_PROCESS_COMPLETED"
    # WIP data
    DEMOGRAPHICS_UPDATED = "DEMOGRAPHICS_UPDATED"
    SYMPTOMS_UPDATED = "SYMPTOMS_UPDATED"
    CONTEXT_UPDATED = "CONTEXT_UPDATED"
    COMPLETENESS_CALCULATED = "COMPLETENESS_CALCULATED"
    # SOAP
    SOAP_GENERATION_STARTED = "SOAP_GENERATION_STARTED"
    SOAP_SECTION_COMPLETED = "SOAP_SECTION_COMPLETED"
    SOAP_GENERATION_COMPLETED = "SOAP_GENERATION_COMPLETED"
    SOAP_GENERATION_FAILED = "SOAP_GENERATION_FAILED"
    # Urgency
    CRITICAL_PATTERN_DETECTED = "CRITICAL_PATTERN_DETECTED"
    URGENCY_CLASSIFIED = "URGENCY_CLASSIFIED"
    # LLM decisions
    LLM_CALL_INITIATED = "LLM_CALL_INITIATED"
    LLM_CALL_COMPLETED = "LLM_CALL_COMPLETED"
    LLM_CALL_FAILED = "LLM_CALL_FAILED"
    # Audit
    AUDIT_ENTRY_CREATED = "AUDIT_ENTRY_CREATED"
    # System
    CORE_STATE_CHANGED = "CORE_STATE_CHANGED"
    CORE_ERROR_OCCURRED = "CORE_ERROR_OCCURRED"


#: Redux action type → domain EventType (docs/MAPPING.json).
ACTION_TO_EVENT_MAP: dict[str, EventType] = {
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
    # WIP data
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
    # Cognitive / urgency
    "cognitive/addCognitiveEvent": EventType.CRITICAL_PATTERN_DETECTED,
    "cognitive/updateSystemHealth": EventType.URGENCY_CLASSIFIED,
    # LLM decisions
    "decisions/startDecision": EventType.LLM_CALL_INITIATED,
    "decisions/completeDecision": EventType.LLM_CALL_COMPLETED,
    "decisions/failDecision": EventType.LLM_CALL_FAILED,
    # Audit
    "decisions/addAuditEntries": EventType.AUDIT_ENTRY_CREATED,
    # System
    "medicalChat/setCoreLoading": EventType.CORE_STATE_CHANGED,
    "medicalChat/setCoreError": EventType.CORE_ERROR_OCCURRED,
}


def sha256_payload(data: Any) -> str:
    """Stable SHA256 of a JSON-serializable payload (for audit non-repudiation)."""
    encoded = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class EventMetadata:
    """Audit/traceability metadata attached to every event."""

    user_id: str
    session_id: str
    source: str = "fi_core.cognitive"
    timezone: str = "America/Mexico_City"


@dataclass
class DomainEvent:
    """An immutable consultation domain event for the event store."""

    consultation_id: str
    event_type: EventType
    payload: dict[str, Any]
    metadata: EventMetadata
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    audit_hash: str | None = None


class PayloadTranslator:
    """Pure functions mapping Redux payloads → event payloads (MAPPING.json)."""

    @staticmethod
    def add_message(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "message_content": p.get("content"),
            "message_role": p.get("type"),  # 'user' | 'assistant'
            "metadata": p.get("metadata", {}),
        }

    @staticmethod
    def update_message(p: dict[str, Any]) -> dict[str, Any]:
        return {"message_id": p.get("messageId"), "updated_content": p.get("content")}

    @staticmethod
    def delete_message(p: dict[str, Any]) -> dict[str, Any]:
        return {"message_id": p.get("messageId")}

    @staticmethod
    def extraction_started(p: dict[str, Any]) -> dict[str, Any]:
        meta_arg = p.get("meta", {}).get("arg", {})
        return {
            "iteration": 1,
            "context_message_count": len(meta_arg.get("messages", [])),
            "has_previous_extraction": meta_arg.get("currentExtraction") is not None,
        }

    @staticmethod
    def extraction_completed(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "iteration": p.get("iteration", 1),
            "completeness": p.get("completenessPercentage", 0),
            "nom_compliance": p.get("nomCompliance", 0),
            "missing_fields": p.get("missingFields", []),
            "extraction_data": p.get("extraction", {}),
        }

    @staticmethod
    def extraction_failed(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "iteration": p.get("iteration", 1),
            "error_message": p.get("error", "Unknown error"),
            "error_type": p.get("errorType", "extraction_error"),
        }

    @staticmethod
    def demographics(p: dict[str, Any]) -> dict[str, Any]:
        return {k: p.get(k) for k in ("age", "gender", "weight", "height", "occupation")}

    @staticmethod
    def symptoms(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "primary_symptoms": p.get("primarySymptoms", []),
            "secondary_symptoms": p.get("secondarySymptoms"),
            "duration": p.get("duration"),
            "severity": p.get("severity"),
            "location": p.get("location"),
            "quality": p.get("quality"),
            "aggravating_factors": p.get("aggravatingFactors"),
            "relieving_factors": p.get("relievingFactors"),
        }

    @staticmethod
    def context(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "past_medical_history": p.get("pastMedicalHistory"),
            "family_history": p.get("familyHistory"),
            "medications": p.get("medications"),
            "allergies": p.get("allergies"),
            "surgeries": p.get("surgeries"),
        }

    @staticmethod
    def completeness(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "completeness_percentage": p.get("percentage", 0),
            "missing_critical_fields": p.get("missingCriticalFields", []),
        }

    @staticmethod
    def soap_section(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "section_name": p.get("section"),
            "section_content": p.get("content"),
            "confidence": p.get("confidence", 0.0),
        }

    @staticmethod
    def soap_completed(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "soap_data": p.get("analysis", {}),
            "quality_score": p.get("quality", 0.0),
            "ready_for_commit": True,
        }

    @staticmethod
    def soap_failed(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "error_message": p.get("error", "Unknown error"),
            "partial_soap": p.get("partialSoap"),
        }

    @staticmethod
    def critical_pattern(p: dict[str, Any]) -> dict[str, Any]:
        data = p.get("data", {})
        return {
            "pattern_name": p.get("eventType", "unknown"),
            "gravity_score": data.get("gravityScore", 5),
            "widow_maker_alert": data.get("widowMakerAlert", False),
            "symptoms_matched": data.get("symptomsMatched", []),
            "critical_differentials": data.get("criticalDifferentials", []),
            "time_to_action": data.get("timeToAction", "unknown"),
        }

    @staticmethod
    def urgency(p: dict[str, Any]) -> dict[str, Any]:
        metrics = p.get("metrics", {})
        return {
            "urgency_level": p.get("health", "medium"),
            "gravity_score": metrics.get("gravityScore", 5),
            "time_to_action": metrics.get("timeToAction", "unknown"),
            "identified_patterns": metrics.get("identifiedPatterns", []),
            "risk_factors": metrics.get("riskFactors", []),
        }

    @staticmethod
    def llm_initiated(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision_id": p.get("id"),
            "llm_provider": p.get("provider", "claude"),
            "query_text": p.get("query", ""),
            "agent_name": p.get("agentName"),
        }

    @staticmethod
    def llm_completed(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision_id": p.get("id"),
            "llm_provider": p.get("provider", "claude"),
            "decision_result": p.get("decision"),
            "confidence": p.get("confidence", 0.0),
            "latency_ms": p.get("latency", 0),
            "tokens_used": p.get("tokensUsed"),
        }

    @staticmethod
    def llm_failed(p: dict[str, Any]) -> dict[str, Any]:
        return {
            "decision_id": p.get("id"),
            "error_message": p.get("error", "Unknown error"),
            "retry_count": p.get("retryCount", 0),
        }

    @staticmethod
    def audit_entries(p: Any) -> dict[str, Any]:
        return {"audit_entries": p if isinstance(p, list) else [p]}

    @staticmethod
    def consultation_committed(p: dict[str, Any]) -> dict[str, Any]:
        soap_data = p.get("finalAnalysis", {})
        return {
            "soap_data": soap_data,
            "committed_by": p.get("committedBy", "user_id"),
            "commit_hash": sha256_payload(soap_data),
            "quality_score": soap_data.get("quality_score", 0.0),
            "completeness": soap_data.get("completeness", 0.0),
            "nom_compliance": soap_data.get("nom_compliance", 0.0),
        }


# Action type → payload translator (actions without an entry pass payload through).
_TRANSLATORS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "medicalChat/addMessage": PayloadTranslator.add_message,
    "medicalChat/updateMessage": PayloadTranslator.update_message,
    "medicalChat/deleteMessage": PayloadTranslator.delete_message,
    "medicalChat/extractMedicalData/pending": PayloadTranslator.extraction_started,
    "medicalChat/extractMedicalData/fulfilled": PayloadTranslator.extraction_completed,
    "medicalChat/extractMedicalData/rejected": PayloadTranslator.extraction_failed,
    "medicalChat/updateDemographics": PayloadTranslator.demographics,
    "medicalChat/updateSymptoms": PayloadTranslator.symptoms,
    "medicalChat/updateContext": PayloadTranslator.context,
    "medicalChat/updateCompleteness": PayloadTranslator.completeness,
    "soapAnalysisReal/updateSOAPSection": PayloadTranslator.soap_section,
    "soapAnalysisReal/extractionSuccess": PayloadTranslator.soap_completed,
    "soapAnalysisReal/extractionError": PayloadTranslator.soap_failed,
    "soapAnalysisReal/completeAnalysis": PayloadTranslator.consultation_committed,
    "cognitive/addCognitiveEvent": PayloadTranslator.critical_pattern,
    "cognitive/updateSystemHealth": PayloadTranslator.urgency,
    "decisions/startDecision": PayloadTranslator.llm_initiated,
    "decisions/completeDecision": PayloadTranslator.llm_completed,
    "decisions/failDecision": PayloadTranslator.llm_failed,
    "decisions/addAuditEntries": PayloadTranslator.audit_entries,
}


def validate_redux_action(redux_action: Any) -> bool:
    """Whether ``redux_action`` is a dict with a string ``type``."""
    return (
        isinstance(redux_action, dict)
        and isinstance(redux_action.get("type"), str)
    )


def action_to_event_type(action_type: str) -> EventType | None:
    """Look up the domain EventType for a Redux action type (None if unmapped)."""
    return ACTION_TO_EVENT_MAP.get(action_type)


class ReduxEventAdapter:
    """Translate Redux actions into :class:`DomainEvent`s for an event store."""

    def translate_action(
        self,
        redux_action: dict[str, Any],
        consultation_id: str,
        user_id: str,
        session_id: str | None = None,
        *,
        audit: bool = False,
    ) -> DomainEvent:
        """Translate one Redux action. Raises ``ValueError`` on unknown types."""
        action_type = redux_action.get("type")
        if action_type not in ACTION_TO_EVENT_MAP:
            raise ValueError(f"Unknown Redux action type: {action_type!r}")

        redux_payload = redux_action.get("payload", {})
        translator = _TRANSLATORS.get(action_type)
        payload = translator(redux_payload) if translator else redux_payload

        event = DomainEvent(
            consultation_id=consultation_id,
            event_type=ACTION_TO_EVENT_MAP[action_type],
            payload=payload,
            metadata=EventMetadata(
                user_id=user_id,
                session_id=session_id or str(uuid4()),
                source="redux_adapter",
            ),
        )
        if audit:
            event.audit_hash = sha256_payload(payload)
        return event

    def translate_batch(
        self,
        redux_actions: list[dict[str, Any]],
        consultation_id: str,
        user_id: str,
        session_id: str | None = None,
        *,
        skip_unknown: bool = True,
    ) -> list[DomainEvent]:
        """Translate a batch (e.g. replaying Redux history). Skips unknowns by default."""
        events: list[DomainEvent] = []
        for action in redux_actions:
            try:
                events.append(
                    self.translate_action(action, consultation_id, user_id, session_id)
                )
            except ValueError:
                if not skip_unknown:
                    raise
        return events
