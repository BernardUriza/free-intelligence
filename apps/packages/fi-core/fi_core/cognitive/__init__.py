"""fi_core.cognitive — medical cognitive-flow primitives.

Prompt presets distilled from real production medical AI consumers (intake,
SOAP generation, triage/urgency, medication extraction, emotion, diarization,
corpus search), exposed as typed :class:`CognitivePreset` objects. These 7
presets are the *prompt layer* of the Redux-Claude clinical state machine.

The core (types + discovery) is zero-dep. Loading a preset's YAML requires
the ``cognitive`` extra::

    pip install 'fi-core[cognitive]'

    from fi_core.cognitive import available_presets, load_preset
    print(available_presets())
    p = load_preset("intake_coach")
    print(p.name, p.llm.provider, p.llm.model)
    print(p.system_prompt[:120])
    print(p.get("urgency_rules"))  # preset-specific fields via .get()
"""

from .domains import (
    CARDIOLOGY,
    DOMAINS,
    PSYCHIATRY,
    ClinicalDomain,
)
from .events import (
    ACTION_TO_EVENT_MAP,
    DomainEvent,
    EventMetadata,
    EventType,
    PayloadTranslator,
    ReduxEventAdapter,
    action_to_event_type,
    sha256_payload,
    validate_redux_action,
)
from .extraction import (
    COMPLETENESS_THRESHOLD,
    FOCUS_LABELS,
    FOCUS_STRATEGY,
    MAX_ITERATIONS,
    ExtractionLoop,
    IterationDecision,
    decide_next_iteration,
    focus_for_iteration,
)
from .loader import available_presets, load_all, load_preset
from .mcp_contract import MCP_SERVER_NAME, MCP_TOOLS
from .soap import (
    COMMIT_COMPLETENESS_THRESHOLD,
    COMMIT_NOM_THRESHOLD,
    SECTION_WEIGHTS,
    Assessment,
    CompletenessMetrics,
    Objective,
    Plan,
    SOAPSection,
    Subjective,
    calculate_soap_completeness,
)
from .state_machine import (
    SUGGESTED_STATE_PRESETS,
    TERMINAL_STATES,
    TRANSITIONS,
    ConsultationState,
    ConsultationStateMachine,
    InvalidTransition,
    Trigger,
    transitions_from,
)
from .types import CognitivePreset, LLMConfig
from .urgency import (
    URGENCY_BANDS,
    GravityScore,
    PatientContext,
    UrgencyBand,
    UrgencyClassifier,
    UrgencyLevel,
    band_for_gravity,
)

__all__ = [
    "ACTION_TO_EVENT_MAP",
    "CARDIOLOGY",
    "COMMIT_COMPLETENESS_THRESHOLD",
    "COMMIT_NOM_THRESHOLD",
    # extraction iteration
    "COMPLETENESS_THRESHOLD",
    "DOMAINS",
    "FOCUS_LABELS",
    "FOCUS_STRATEGY",
    "MAX_ITERATIONS",
    # mcp contract (server lives in fi_core.cognitive.mcp_server, needs [mcp])
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
    "PSYCHIATRY",
    "SECTION_WEIGHTS",
    "SUGGESTED_STATE_PRESETS",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "URGENCY_BANDS",
    "Assessment",
    # clinical domains (specialty vocabularies for triage)
    "ClinicalDomain",
    # presets
    "CognitivePreset",
    "CompletenessMetrics",
    # state machine
    "ConsultationState",
    "ConsultationStateMachine",
    "DomainEvent",
    "EventMetadata",
    # redux → events
    "EventType",
    "ExtractionLoop",
    "GravityScore",
    "InvalidTransition",
    "IterationDecision",
    "LLMConfig",
    "Objective",
    "PatientContext",
    "PayloadTranslator",
    "Plan",
    "ReduxEventAdapter",
    # soap progression
    "SOAPSection",
    "Subjective",
    "Trigger",
    "UrgencyBand",
    "UrgencyClassifier",
    # urgency / triage
    "UrgencyLevel",
    "action_to_event_type",
    "available_presets",
    "band_for_gravity",
    "calculate_soap_completeness",
    "decide_next_iteration",
    "focus_for_iteration",
    "load_all",
    "load_preset",
    "sha256_payload",
    "transitions_from",
    "validate_redux_action",
]
