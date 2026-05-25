"""The clinical consultation state machine.

A zero-dep, deterministic finite-state machine extracted faithfully from the
Redux-Claude Medical AI flow spec (``docs/archive/FLOW.md`` in the
free-intelligence repo). It models the *control flow* of a medical
consultation — intake → validation → iterative extraction → SOAP → assessment
→ plan → commit, with an EMERGENCY/TRIAGE fast path and an ERROR/retry path.

This is the orchestration skeleton; the prompt layer for each step lives in
:mod:`fi_core.cognitive` presets (see :data:`SUGGESTED_STATE_PRESETS`). The
sub-machines (extraction iteration, SOAP progression, urgency classification)
described in FLOW.md are intentionally out of scope for this module.

Example::

    sm = ConsultationStateMachine()
    sm.fire(Trigger.START)            # IDLE -> INTAKE
    sm.fire(Trigger.MESSAGE)          # INTAKE -> VALIDATING
    sm.fire(Trigger.VALID_MEDICAL)    # VALIDATING -> EXTRACTING
    print(sm.state, sm.available_triggers())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConsultationState(str, Enum):
    """The primary states of a consultation (FLOW.md §1)."""

    IDLE = "IDLE"
    INTAKE = "INTAKE"
    VALIDATING = "VALIDATING"
    EXTRACTING = "EXTRACTING"
    WIP_UPDATE = "WIP_UPDATE"
    SOAP_GENERATION = "SOAP_GENERATION"
    ASSESSMENT = "ASSESSMENT"
    PLAN_CREATION = "PLAN_CREATION"
    READY_TO_COMMIT = "READY_TO_COMMIT"
    COMMITTED = "COMMITTED"
    EMERGENCY = "EMERGENCY"
    TRIAGE = "TRIAGE"
    RESPONDING = "RESPONDING"
    ERROR = "ERROR"


class Trigger(str, Enum):
    """The events that drive transitions between states (FLOW.md transitions)."""

    START = "start"  # user starts consultation
    MESSAGE = "message"  # user sends message
    VALID_MEDICAL = "valid_medical"  # validated as medical input
    GENERAL_QUESTION = "general_question"  # non-clinical question
    CRITICAL_PATTERN = "critical_pattern"  # critical pattern detected
    FAIL = "fail"  # validation/extraction/generation failed
    PARTIAL_DATA = "partial_data"  # partial data extracted
    NEEDS_MORE = "needs_more"  # needs another extraction iteration
    COMPLETENESS_REACHED = "completeness_reached"  # >=80% or max iterations
    SOAP_COMPLETE = "soap_complete"
    DIAGNOSIS_CONFIRMED = "diagnosis_confirmed"
    PLAN_COMPLETE = "plan_complete"
    URGENCY_CLASSIFIED = "urgency_classified"
    EMERGENCY_SOAP = "emergency_soap"  # expedited SOAP after triage
    USER_CONFIRMS = "user_confirms"
    REQUEST_CHANGES = "request_changes"  # user requests edits at review
    CONTINUE = "continue"  # continue general conversation
    RETRY = "retry"  # retry after error


# Transition table: (from_state, trigger) -> to_state. Mirrors the mermaid
# stateDiagram in FLOW.md §1 plus the per-state "Transitions" definitions.
TRANSITIONS: tuple[tuple[ConsultationState, Trigger, ConsultationState], ...] = (
    (ConsultationState.IDLE, Trigger.START, ConsultationState.INTAKE),
    (ConsultationState.INTAKE, Trigger.MESSAGE, ConsultationState.VALIDATING),
    (ConsultationState.VALIDATING, Trigger.VALID_MEDICAL, ConsultationState.EXTRACTING),
    (ConsultationState.VALIDATING, Trigger.GENERAL_QUESTION, ConsultationState.RESPONDING),
    (ConsultationState.VALIDATING, Trigger.CRITICAL_PATTERN, ConsultationState.EMERGENCY),
    (ConsultationState.VALIDATING, Trigger.FAIL, ConsultationState.ERROR),
    (ConsultationState.EXTRACTING, Trigger.PARTIAL_DATA, ConsultationState.WIP_UPDATE),
    (ConsultationState.EXTRACTING, Trigger.FAIL, ConsultationState.ERROR),
    (ConsultationState.WIP_UPDATE, Trigger.NEEDS_MORE, ConsultationState.EXTRACTING),
    (ConsultationState.WIP_UPDATE, Trigger.COMPLETENESS_REACHED, ConsultationState.SOAP_GENERATION),
    (ConsultationState.WIP_UPDATE, Trigger.FAIL, ConsultationState.ERROR),
    (ConsultationState.SOAP_GENERATION, Trigger.SOAP_COMPLETE, ConsultationState.ASSESSMENT),
    (ConsultationState.SOAP_GENERATION, Trigger.FAIL, ConsultationState.ERROR),
    (ConsultationState.ASSESSMENT, Trigger.DIAGNOSIS_CONFIRMED, ConsultationState.PLAN_CREATION),
    (ConsultationState.PLAN_CREATION, Trigger.PLAN_COMPLETE, ConsultationState.READY_TO_COMMIT),
    (ConsultationState.EMERGENCY, Trigger.URGENCY_CLASSIFIED, ConsultationState.TRIAGE),
    (ConsultationState.TRIAGE, Trigger.EMERGENCY_SOAP, ConsultationState.SOAP_GENERATION),
    (ConsultationState.READY_TO_COMMIT, Trigger.USER_CONFIRMS, ConsultationState.COMMITTED),
    (ConsultationState.READY_TO_COMMIT, Trigger.REQUEST_CHANGES, ConsultationState.INTAKE),
    (ConsultationState.RESPONDING, Trigger.CONTINUE, ConsultationState.INTAKE),
    (ConsultationState.ERROR, Trigger.RETRY, ConsultationState.INTAKE),
)

#: States with no outgoing transitions — the consultation is finished.
TERMINAL_STATES: frozenset[ConsultationState] = frozenset({ConsultationState.COMMITTED})

# Best-effort binding of a state to one of the bundled prompt presets. Only the
# unambiguous ones are mapped — the rest are left open on purpose (mapping every
# step would be guessing). Use this as a starting point, not gospel.
SUGGESTED_STATE_PRESETS: dict[ConsultationState, str] = {
    ConsultationState.INTAKE: "intake_coach",
    ConsultationState.EXTRACTING: "question_generator",
    ConsultationState.SOAP_GENERATION: "soap_generator",
}

_TRANSITION_MAP: dict[tuple[ConsultationState, Trigger], ConsultationState] = {
    (src, trig): dst for src, trig, dst in TRANSITIONS
}


class InvalidTransition(Exception):
    """Raised when a trigger is fired that is not valid from the current state."""


@dataclass
class ConsultationStateMachine:
    """A live consultation FSM. Starts in :attr:`ConsultationState.IDLE`."""

    state: ConsultationState = ConsultationState.IDLE
    history: list[ConsultationState] = field(default_factory=list)

    def available_triggers(self) -> list[Trigger]:
        """Triggers that can fire from the current state."""
        return [trig for (src, trig) in _TRANSITION_MAP if src == self.state]

    def can(self, trigger: Trigger) -> bool:
        """Whether ``trigger`` is valid from the current state."""
        return (self.state, trigger) in _TRANSITION_MAP

    def fire(self, trigger: Trigger) -> ConsultationState:
        """Apply ``trigger``, advancing the state. Raises :class:`InvalidTransition`."""
        key = (self.state, trigger)
        if key not in _TRANSITION_MAP:
            allowed = [t.value for t in self.available_triggers()]
            raise InvalidTransition(
                f"{trigger.value!r} is not valid from {self.state.value!r}; "
                f"allowed: {allowed}"
            )
        self.history.append(self.state)
        self.state = _TRANSITION_MAP[key]
        return self.state

    def is_terminal(self) -> bool:
        """Whether the consultation has reached a terminal state."""
        return self.state in TERMINAL_STATES

    def reset(self) -> None:
        """Return to IDLE, clearing history."""
        self.state = ConsultationState.IDLE
        self.history.clear()


def transitions_from(state: ConsultationState) -> dict[Trigger, ConsultationState]:
    """All ``trigger -> next_state`` edges leaving ``state`` (for introspection/diagrams)."""
    return {trig: dst for (src, trig), dst in _TRANSITION_MAP.items() if src == state}
