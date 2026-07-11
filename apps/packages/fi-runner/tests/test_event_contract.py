"""Contract tests — every frame the runner emits MUST validate against the SSOT.

This is the test that did not exist. Before it, the wire contract lived in two
hand-maintained copies (Python dict literals here, a TypeScript ``mapEvent``
switch in the web client) and nothing compared them. A field renamed on one side
reached production as a silently-dropped frame.

Now every emitter path runs through :func:`fi_runner.events.validate_event`. A
drift fails CI here, at the source, instead of in a client at runtime.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from pydantic import ValidationError  # noqa: E402

from fi_runner._plan_events import _derive_plan_events, _PlanStreamObserver  # noqa: E402
from fi_runner.backend import ToolCall, TurnResult  # noqa: E402
from fi_runner.events import json_schema, validate_event  # noqa: E402

TRACKER = "fi_core_task_tracker"


def _tracker_call(tool: str, **inp: object) -> ToolCall:
    return ToolCall(
        name=f"mcp__{TRACKER}__{tool}",
        server=TRACKER,
        input=dict(inp),
    )


def _derive(tool: str, *, observer: _PlanStreamObserver | None = None, **inp: object):
    return _derive_plan_events(
        _tracker_call(tool, **inp),
        session_id="sess-1",
        request_id="req-1",
        observer=observer,
    )


class TestPlanFamilyEmitsValidFrames:
    def test_declare_plan(self):
        events = _derive("declare_plan", steps=["uno", "dos"])
        assert events
        model = validate_event(events[0])
        assert model.type == "plan"
        assert model.data.steps == ["uno", "dos"]
        assert model.data.request_id == "req-1"

    def test_start_step(self):
        events = _derive("start_step", plan_id="p1", step_index=0)
        model = validate_event(events[0])
        assert model.type == "step_started"
        assert model.data.step_index == 0

    @pytest.mark.parametrize(
        ("tool", "status"),
        [("complete_step", "done"), ("fail_step", "failed"), ("cancel_step", "cancelled")],
    )
    def test_step_settlements(self, tool: str, status: str):
        events = _derive(tool, plan_id="p1", step_index=1, summary="ok", error="boom")
        model = validate_event(events[0])
        assert model.type == "step_done"
        assert model.data.status == status

    def test_note_step(self):
        events = _derive("note_step", plan_id="p1", step_index=0, note="ojo")
        model = validate_event(events[0])
        assert model.type == "step_noted"
        assert model.data.note == "ojo"

    @pytest.mark.parametrize(
        ("tool", "action"), [("insert_step", "insert"), ("replan", "replan")]
    )
    def test_plan_amended(self, tool: str, action: str):
        events = _derive(tool, plan_id="p1")
        model = validate_event(events[0])
        assert model.type == "plan_amended"
        assert model.data.action == action

    def test_cancel_plan(self):
        events = _derive("cancel_plan", plan_id="p1", reason="ya no")
        model = validate_event(events[0])
        assert model.type == "plan_cancelled"
        assert model.data.reason == "ya no"

    def test_finalize_plan_with_observer_carries_counts(self):
        observer = _PlanStreamObserver()
        _derive("complete_step", observer=observer, plan_id="p1", step_index=0)
        events = _derive("finalize_plan", observer=observer, plan_id="p1")
        model = validate_event(events[0])
        assert model.type == "plan_completed"
        assert model.data.completed_count == 1

    def test_finalize_plan_without_observer_still_carries_counts(self):
        """The no-observer branch used to omit the counters entirely, so a client
        coerced ``undefined`` to 0 and never knew the difference. The contract
        now defaults them, so the frame is complete either way."""
        events = _derive("finalize_plan", plan_id="p1")
        model = validate_event(events[0])
        assert model.type == "plan_completed"
        assert model.data.completed_count == 0
        assert model.data.failed_count == 0
        assert model.data.cancelled_count == 0

    def test_failed_plan_selected_when_a_step_failed(self):
        observer = _PlanStreamObserver()
        _derive("fail_step", observer=observer, plan_id="p1", step_index=0, error="x")
        events = _derive("finalize_plan", observer=observer, plan_id="p1")
        model = validate_event(events[0])
        assert model.type == "plan_failed"
        assert model.data.failed_count == 1


class TestBackendFramesValidate:
    def test_text_delta(self):
        assert validate_event({"type": "text", "text": "hola"}).text == "hola"

    def test_tool_call_frame(self):
        tool = ToolCall.make("Bash", input={"cmd": "ls"}, id="t1", duration_ms=12)
        frame = {
            "type": "tool_call",
            "tool": {
                "name": tool.name,
                "server": tool.server,
                "input": tool.input,
                "id": tool.id,
                "is_error": tool.is_error,
                "duration_ms": tool.duration_ms,
            },
        }
        model = validate_event(frame)
        assert model.tool.name == "Bash"
        assert model.tool.duration_ms == 12

    def test_result_frame(self):
        result = TurnResult(text="listo", session_id="s1")
        frame = {
            "type": "result",
            "result": {
                "text": result.text,
                "usage": result.usage,
                "session_id": result.session_id,
                "guard_outcomes": {},
                "tool_calls": [],
            },
        }
        assert validate_event(frame).result.text == "listo"


class TestTransportFramesValidate:
    def test_open(self):
        assert validate_event({"type": "open", "request_id": "req-1"}).request_id == "req-1"

    def test_element(self):
        """The frame that says WHO answered. The web client had no case for it and
        dropped it on the floor — the contract makes its existence undeniable."""
        frame = {"type": "element", "element": {"id": "O", "label": "Oxígeno"}}
        assert validate_event(frame).element.label == "Oxígeno"

    def test_error(self):
        assert validate_event({"type": "error", "message": "tronó"}).message == "tronó"

    def test_done(self):
        assert validate_event({"type": "done"}).type == "done"


class TestContractRejectsDrift:
    def test_unknown_event_type_is_rejected(self):
        with pytest.raises(ValidationError):
            validate_event({"type": "inventado", "data": {}})

    def test_renamed_field_is_rejected(self):
        """A field renamed on the emitter (``step_index`` → ``index``) is exactly
        the drift that used to reach clients as a silent ``-1``."""
        with pytest.raises(ValidationError):
            validate_event({"type": "step_started", "data": {"plan_id": "p1", "index": 0}})

    def test_missing_required_field_is_rejected(self):
        with pytest.raises(ValidationError):
            validate_event({"type": "text"})

    def test_invalid_step_status_is_rejected(self):
        with pytest.raises(ValidationError):
            validate_event(
                {"type": "step_done", "data": {"step_index": 0, "status": "maybe"}}
            )


class TestCommittedSchemaIsFresh:
    """The guard that keeps the SSOT from rotting.

    ``contracts/agent-events.schema.json`` is the artifact every downstream
    codegen reads (TypeScript for the web, Swift for iOS). If someone edits
    ``events.py`` and forgets to regenerate it, the clients silently compile
    against a stale contract. This test makes that impossible: the committed
    file must be byte-identical to a fresh export.

    Regenerate with:
        python -m fi_runner.events > contracts/agent-events.schema.json
    """

    def test_committed_schema_matches_the_models(self):
        import json
        from pathlib import Path

        committed_path = Path(__file__).resolve().parents[1] / "contracts" / "agent-events.schema.json"
        assert committed_path.exists(), (
            "contracts/agent-events.schema.json is missing — regenerate it with "
            "`python -m fi_runner.events > contracts/agent-events.schema.json`"
        )
        committed = json.loads(committed_path.read_text())
        assert committed == json_schema(), (
            "The committed schema is STALE — events.py changed without regenerating it. "
            "Run: python -m fi_runner.events > contracts/agent-events.schema.json"
        )


class TestSchemaIsExportable:
    def test_schema_has_every_event_variant(self):
        schema = json_schema()
        variants = {name for name in schema["$defs"] if name.endswith("Event")}
        expected = {
            "OpenEvent",
            "ElementEvent",
            "TextEvent",
            "ToolCallEvent",
            "ResultEvent",
            "PlanEvent",
            "StepStartedEvent",
            "StepDoneEvent",
            "StepNotedEvent",
            "PlanAmendedEvent",
            "PlanCancelledEvent",
            "PlanCompletedEvent",
            "PlanFailedEvent",
            "PlanRejectedEvent",
            "ErrorEvent",
            "DoneEvent",
        }
        assert expected <= variants

    def test_schema_discriminates_on_type(self):
        assert json_schema()["discriminator"]["propertyName"] == "type"
