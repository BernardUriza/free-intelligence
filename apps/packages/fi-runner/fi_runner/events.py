"""The agent stream contract — SINGLE SOURCE OF TRUTH for every wire consumer.

This module is the ONLY authoritative definition of the frames that travel over
the wire (SSE) from a fi-runner stream to any consumer: the web app, an iOS app,
a CLI, a test harness. Before it existed the contract lived implicitly in two
places at once — raw ``dict`` literals in :mod:`fi_runner._plan_events` (Python)
and a hand-written ``mapEvent`` switch in the og118 web client (TypeScript) —
with nothing keeping them honest. Every drift between them was a production bug
nobody could see (an ``element`` frame the client silently dropped; plan counters
that arrived ``undefined``; step indices that landed on ``-1``).

From here, and only from here, we derive:

- the JSON Schema (``python -m fi_runner.events`` → ``agent-events.schema.json``)
- the TypeScript types consumed by ``@free-intelligence/core``
- the Swift types consumed by a native iOS client
- the ``/chat/stream`` frame documentation in a consumer's OpenAPI

Envelope shapes. The wire is a discriminated union keyed on ``type``. Three
shapes coexist, and that is fine — each variant declares its own payload:

- ``{"type": "text", "text": "..."}``                    — flat payload
- ``{"type": "tool_call", "tool": {...}}``               — payload under its own key
- ``{"type": "plan", "data": {...}}``                    — the plan family nests in ``data``

Dependency note. fi-runner's runtime is deliberately zero-dep (see
``pyproject.toml``); pydantic is therefore an OPTIONAL extra:

    pip install 'fi-runner[contract]'

The Runner never imports this module on its hot path — it keeps yielding plain
dicts. These models are the SPECIFICATION those dicts must satisfy, enforced by
the contract tests and consumed by codegen. Importing ``fi_runner`` stays dep-free.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

SCHEMA_VERSION = "1.0.0"


class ToolCallPayload(BaseModel):
    """One tool invocation, mirroring :class:`fi_runner.backend.ToolCall`.

    ``input`` may carry PHI and is never placed in telemetry; it stays on the
    wire only because the glass-box panel renders it for the operator.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    server: str | None = None
    input: dict[str, Any] | None = None
    id: str | None = None
    is_error: bool | None = None
    duration_ms: int | None = None


class TurnResultPayload(BaseModel):
    """The settled result of a turn, mirroring :class:`fi_runner.backend.TurnResult`.

    ``model`` is the model that ACTUALLY ran (the retry loop may escalate to the
    fallback), so a UI shows the answer's real provenance instead of guessing at
    the configured default.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    usage: dict[str, Any] | None = None
    session_id: str | None = None
    model: str | None = None
    guard_outcomes: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[ToolCallPayload] = Field(default_factory=list)


class ElementPayload(BaseModel):
    """Which persona/element answered this turn.

    ``label`` is the composed one-liner ("53 · I · Yodo"); the parts ride
    alongside it so a UI can attribute a bubble without re-parsing that string —
    ``name`` is the speaker's name, ``symbol`` the avatar token, ``engine`` the
    persona/engine behind it. Optional: a runner that only knows an id/label
    still emits a valid frame.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    name: str | None = None
    symbol: str | None = None
    engine: str | None = None


class OpenEvent(BaseModel):
    """First frame of every stream. Carries the id a UI keys concurrent turns on."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["open"] = "open"
    request_id: str | None = None


class ElementEvent(BaseModel):
    """Announces WHO is answering, before any token arrives."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["element"] = "element"
    element: ElementPayload


class TextEvent(BaseModel):
    """A token delta. Consumers append; they never replace."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["text"] = "text"
    text: str


class ToolCallEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["tool_call"] = "tool_call"
    tool: ToolCallPayload


class ResultEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["result"] = "result"
    result: TurnResultPayload


class PlanData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[str]
    session_id: str | None = None
    request_id: str | None = None


class PlanEvent(BaseModel):
    """The agent declared its plan. ``steps`` is the checklist a UI renders."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["plan"] = "plan"
    data: PlanData


class StepStartedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    step_index: int
    request_id: str | None = None


class StepStartedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["step_started"] = "step_started"
    data: StepStartedData


class StepDoneData(BaseModel):
    """``summary`` accompanies a ``done`` step; ``error`` a failed/cancelled one."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    step_index: int
    status: Literal["done", "failed", "cancelled"]
    summary: str | None = None
    error: str | None = None
    request_id: str | None = None


class StepDoneEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["step_done"] = "step_done"
    data: StepDoneData


class StepNotedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    step_index: int
    note: str
    request_id: str | None = None


class StepNotedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["step_noted"] = "step_noted"
    data: StepNotedData


class PlanAmendedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    action: Literal["insert", "replan"]
    request_id: str | None = None


class PlanAmendedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["plan_amended"] = "plan_amended"
    data: PlanAmendedData


class PlanCancelledData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    reason: str = ""
    request_id: str | None = None


class PlanCancelledEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["plan_cancelled"] = "plan_cancelled"
    data: PlanCancelledData


class PlanTerminalData(BaseModel):
    """Counters for the terminal plan frame.

    They default to ``0`` rather than being optional on purpose: a consumer must
    never receive ``undefined`` here and coerce it silently. The emitter fills
    real counts whenever the observer ran.
    """

    model_config = ConfigDict(extra="forbid")

    plan_id: str | None = None
    completed_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
    request_id: str | None = None


class PlanCompletedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["plan_completed"] = "plan_completed"
    data: PlanTerminalData


class PlanFailedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["plan_failed"] = "plan_failed"
    data: PlanTerminalData


class GuardMatch(BaseModel):
    model_config = ConfigDict(extra="allow")

    index: int
    label: str


class PlanRejectedData(BaseModel):
    """A plan guard refused the declared plan before any step ran."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    matched: list[GuardMatch] = Field(default_factory=list)
    reinforcement: str | None = None
    guard: str | None = None
    request_id: str | None = None


class PlanRejectedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["plan_rejected"] = "plan_rejected"
    data: PlanRejectedData


class ErrorEvent(BaseModel):
    """The turn died. Terminal — no ``done`` follows a fatal error."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    message: str


class DoneEvent(BaseModel):
    """Last frame of a healthy stream."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["done"] = "done"


AgentStreamEvent = Annotated[
    Union[
        OpenEvent,
        ElementEvent,
        TextEvent,
        ToolCallEvent,
        ResultEvent,
        PlanEvent,
        StepStartedEvent,
        StepDoneEvent,
        StepNotedEvent,
        PlanAmendedEvent,
        PlanCancelledEvent,
        PlanCompletedEvent,
        PlanFailedEvent,
        PlanRejectedEvent,
        ErrorEvent,
        DoneEvent,
    ],
    Field(discriminator="type"),
]

AgentStreamEventAdapter: TypeAdapter[AgentStreamEvent] = TypeAdapter(AgentStreamEvent)


def validate_event(frame: dict[str, Any]) -> AgentStreamEvent:
    """Validate one wire frame against the contract.

    Raises ``pydantic.ValidationError`` when an emitter drifts from the schema.
    The contract tests call this on every frame the Runner yields, so a drift
    breaks CI instead of a client at runtime.
    """
    return AgentStreamEventAdapter.validate_python(frame)


def _strip_property_titles(node: Any) -> Any:
    """Drop pydantic's auto-generated per-property ``title`` keys.

    Pydantic titles every field ("Step Index", "Type", ...). Downstream codegen
    (json-schema-to-typescript) mints a named type alias for each one, so a
    clean union comes out polluted with ``Type1``, ``Text1``, ``Id1``… Model
    titles are kept — those name the real types.
    """
    if isinstance(node, dict):
        cleaned = {
            key: _strip_property_titles(value)
            for key, value in node.items()
            if key != "title"
        }
        return cleaned
    if isinstance(node, list):
        return [_strip_property_titles(item) for item in node]
    return node


def json_schema() -> dict[str, Any]:
    """The JSON Schema of the whole union — the artifact codegen consumes."""
    schema = AgentStreamEventAdapter.json_schema(
        ref_template="#/$defs/{model}",
        mode="serialization",
    )

    defs = schema.get("$defs", {})
    for model_name, model_schema in defs.items():
        properties = model_schema.get("properties", {})
        model_schema["properties"] = {
            field: _strip_property_titles(field_schema)
            for field, field_schema in properties.items()
        }
        model_schema["title"] = model_name

    schema["title"] = "AgentStreamEvent"
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["x-schema-version"] = SCHEMA_VERSION
    schema["description"] = (
        "The fi-runner agent stream contract. Generated from "
        "fi_runner/events.py — do not edit by hand."
    )
    return schema


__all__ = [
    "SCHEMA_VERSION",
    "AgentStreamEvent",
    "AgentStreamEventAdapter",
    "DoneEvent",
    "ElementEvent",
    "ElementPayload",
    "ErrorEvent",
    "GuardMatch",
    "OpenEvent",
    "PlanAmendedEvent",
    "PlanCancelledEvent",
    "PlanCompletedEvent",
    "PlanEvent",
    "PlanFailedEvent",
    "PlanRejectedEvent",
    "ResultEvent",
    "StepDoneEvent",
    "StepNotedEvent",
    "StepStartedEvent",
    "TextEvent",
    "ToolCallEvent",
    "ToolCallPayload",
    "TurnResultPayload",
    "json_schema",
    "validate_event",
]


if __name__ == "__main__":
    print(json.dumps(json_schema(), indent=2))
