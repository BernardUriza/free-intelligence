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
    # presets
    "CognitivePreset",
    "LLMConfig",
    "available_presets",
    "load_preset",
    "load_all",
    # state machine
    "ConsultationState",
    "Trigger",
    "ConsultationStateMachine",
    "InvalidTransition",
    "TRANSITIONS",
    "TERMINAL_STATES",
    "SUGGESTED_STATE_PRESETS",
    "transitions_from",
    # urgency / triage
    "UrgencyLevel",
    "UrgencyBand",
    "URGENCY_BANDS",
    "PatientContext",
    "GravityScore",
    "UrgencyClassifier",
    "band_for_gravity",
    # extraction iteration
    "COMPLETENESS_THRESHOLD",
    "MAX_ITERATIONS",
    "FOCUS_STRATEGY",
    "FOCUS_LABELS",
    "focus_for_iteration",
    "IterationDecision",
    "decide_next_iteration",
    "ExtractionLoop",
    # soap progression
    "SOAPSection",
    "SECTION_WEIGHTS",
    "COMMIT_COMPLETENESS_THRESHOLD",
    "COMMIT_NOM_THRESHOLD",
    "Subjective",
    "Objective",
    "Assessment",
    "Plan",
    "CompletenessMetrics",
    "calculate_soap_completeness",
    # redux → events
    "EventType",
    "ACTION_TO_EVENT_MAP",
    "EventMetadata",
    "DomainEvent",
    "PayloadTranslator",
    "ReduxEventAdapter",
    "action_to_event_type",
    "validate_redux_action",
    "sha256_payload",
    # mcp contract (server lives in fi_core.cognitive.mcp_server, needs [mcp])
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
]
