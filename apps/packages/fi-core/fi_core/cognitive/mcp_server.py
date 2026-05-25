"""MCP server exposing the fi_core.cognitive primitives as agent tools.

A **thin wrapper** over the pure-Python core (`urgency`, `state_machine`,
`extraction`, `soap`, `events`, `loader`) — exactly like
`fi_core.persona.mcp_server` wraps the persona detectors. Each tool just
calls the corresponding core function and returns a JSON-serializable dict;
no logic is duplicated here.

This is the agent-facing transport: a Claude-Agent-SDK / MCP runner registers
it as a stdio subprocess (`python -m fi_core.cognitive.mcp_server`) and calls
`mcp__fi-core-cognitive__classify_urgency`, `__advance_consultation`, etc. The
same primitives remain importable directly for synchronous, non-agent code.

Requires the `mcp` extra (and `cognitive` for preset tools)::

    pip install 'fi-core[mcp,cognitive]'
"""

from __future__ import annotations

import dataclasses
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.cognitive.mcp_server requires the MCP SDK. "
        "Install via: pip install 'fi-core[mcp]'"
    ) from e

from fi_core.cognitive.events import ReduxEventAdapter
from fi_core.cognitive.extraction import decide_next_iteration, focus_for_iteration
from fi_core.cognitive.soap import (
    Assessment,
    Objective,
    Plan,
    Subjective,
    calculate_soap_completeness,
)
from fi_core.cognitive.state_machine import (
    ConsultationState,
    ConsultationStateMachine,
    InvalidTransition,
    Trigger,
    transitions_from,
)
from fi_core.cognitive.urgency import PatientContext, UrgencyClassifier

mcp = FastMCP(
    "fi-core-cognitive",
    instructions=(
        "Clinical cognitive-flow primitives for a medical consultation agent. "
        "Drive a consultation with `advance_consultation` (state machine), "
        "triage symptoms with `classify_urgency`, decide whether to keep "
        "extracting with `decide_extraction`, score a SOAP note with "
        "`score_soap`, fetch a step's prompt with `load_preset`, and turn UI "
        "actions into domain events with `redux_to_event`. Decision support, "
        "not diagnosis."
    ),
)

_URGENCY = UrgencyClassifier()
_REDUX = ReduxEventAdapter()


def _build(cls: type, data: dict[str, Any] | None) -> Any:
    """Build a dataclass from a dict, ignoring unknown keys."""
    valid = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in valid})


# ---------------------------------------------------------------------------
# Presets (prompt layer)
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_presets() -> dict:
    """List the bundled cognitive prompt preset ids."""
    from fi_core.cognitive.loader import available_presets

    return {"presets": available_presets()}


@mcp.tool()
async def load_preset(preset_id: str) -> dict:
    """Load one prompt preset (system prompt + LLM config) by id."""
    from fi_core.cognitive.loader import load_preset as _load

    p = _load(preset_id)
    return {
        "preset_id": p.preset_id,
        "name": p.name,
        "version": p.version,
        "description": p.description,
        "llm": {
            "provider": p.llm.provider,
            "model": p.llm.model,
            "temperature": p.llm.temperature,
            "max_tokens": p.llm.max_tokens,
        },
        "system_prompt": p.system_prompt,
    }


# ---------------------------------------------------------------------------
# State machine (control flow)
# ---------------------------------------------------------------------------


@mcp.tool()
async def available_transitions(state: str) -> dict:
    """List the triggers (and their target states) available from ``state``."""
    try:
        st = ConsultationState(state)
    except ValueError:
        return {
            "error": f"unknown state {state!r}",
            "valid_states": [s.value for s in ConsultationState],
        }
    return {
        "state": st.value,
        "transitions": {t.value: dst.value for t, dst in transitions_from(st).items()},
    }


@mcp.tool()
async def advance_consultation(current_state: str, trigger: str) -> dict:
    """Apply ``trigger`` from ``current_state`` and return the next state."""
    try:
        st = ConsultationState(current_state)
    except ValueError:
        return {
            "error": f"unknown state {current_state!r}",
            "valid_states": [s.value for s in ConsultationState],
        }
    try:
        tr = Trigger(trigger)
    except ValueError:
        return {
            "error": f"unknown trigger {trigger!r}",
            "valid_triggers": [t.value for t in Trigger],
        }
    sm = ConsultationStateMachine(state=st)
    try:
        nxt = sm.fire(tr)
    except InvalidTransition:
        return {
            "error": f"{trigger!r} is not valid from {current_state!r}",
            "available_triggers": [t.value for t in sm.available_triggers()],
        }
    return {
        "previous_state": st.value,
        "trigger": tr.value,
        "next_state": nxt.value,
        "available_triggers": [t.value for t in sm.available_triggers()],
        "is_terminal": sm.is_terminal(),
    }


# ---------------------------------------------------------------------------
# Urgency / triage
# ---------------------------------------------------------------------------


@mcp.tool()
async def classify_urgency(
    symptoms: list[str],
    age: int | None = None,
    gender: str | None = None,
    medical_history: list[str] | None = None,
) -> dict:
    """Triage: compute a 1-10 gravity score and urgency level with reasons."""
    score = _URGENCY.classify(
        PatientContext(
            age=age,
            gender=gender,
            symptoms=list(symptoms or []),
            medical_history=list(medical_history or []),
        )
    )
    return {
        "level": score.level.value,
        "base_gravity": score.base_gravity,
        "modifiers": score.modifiers,
        "final_gravity": score.final_gravity,
        "time_to_action": score.time_to_action,
        "critical_override": score.critical_override,
        "reasons": list(score.reasons),
    }


# ---------------------------------------------------------------------------
# Extraction iteration
# ---------------------------------------------------------------------------


@mcp.tool()
async def decide_extraction(
    completeness: float,
    iteration: int,
    missing_critical_fields: list[str] | None = None,
) -> dict:
    """Decide whether to run another extraction pass (completeness %, max 5)."""
    decision = decide_next_iteration(
        completeness, iteration, tuple(missing_critical_fields or ())
    )
    return {
        "should_continue": decision.should_continue,
        "reason": decision.reason,
        "focus_areas": list(decision.focus_areas),
        "next_iteration_focus": focus_for_iteration(iteration + 1),
    }


# ---------------------------------------------------------------------------
# SOAP progression
# ---------------------------------------------------------------------------


@mcp.tool()
async def score_soap(
    subjective: dict | None = None,
    objective: dict | None = None,
    assessment: dict | None = None,
    plan: dict | None = None,
    nom_violations: list[str] | None = None,
) -> dict:
    """Score SOAP completeness + NOM-004 compliance; report commit readiness."""
    metrics = calculate_soap_completeness(
        _build(Subjective, subjective),
        _build(Objective, objective),
        _build(Assessment, assessment),
        _build(Plan, plan),
        tuple(nom_violations or ()),
    )
    return {
        "percentage": metrics.percentage,
        "sections": metrics.sections,
        "nom_compliance": metrics.nom_compliance,
        "nom_violations": list(metrics.nom_violations),
        "ready_for_commit": metrics.ready_for_commit,
    }


# ---------------------------------------------------------------------------
# Redux → events (event-sourcing)
# ---------------------------------------------------------------------------


@mcp.tool()
async def redux_to_event(
    action_type: str,
    payload: dict | None = None,
    consultation_id: str = "",
    user_id: str = "",
    session_id: str | None = None,
) -> dict:
    """Translate a Redux action into a domain event (raises on unknown types)."""
    try:
        ev = _REDUX.translate_action(
            {"type": action_type, "payload": payload or {}},
            consultation_id=consultation_id,
            user_id=user_id,
            session_id=session_id,
            audit=True,
        )
    except ValueError as exc:
        return {"error": str(exc)}
    return {
        "event_id": ev.event_id,
        "consultation_id": ev.consultation_id,
        "event_type": ev.event_type.value,
        "payload": ev.payload,
        "metadata": dataclasses.asdict(ev.metadata),
        "timestamp": ev.timestamp.isoformat(),
        "audit_hash": ev.audit_hash,
    }


# ---------------------------------------------------------------------------
# Tool contract (single source of truth in mcp_contract — zero-dep) + entry
# ---------------------------------------------------------------------------

from fi_core.cognitive.mcp_contract import (  # noqa: E402  (re-export)
    MCP_SERVER_NAME,
    MCP_TOOLS,
)

__all__ = ["MCP_SERVER_NAME", "MCP_TOOLS", "main", "mcp"]


def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
