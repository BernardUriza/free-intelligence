"""Tests for per-turn flow observability — mechanical diagram + LLM narration.

``events_to_mermaid`` is a pure function over a turn's telemetry. The Runner
ALWAYS publishes a mechanical flow diagram per turn (a ``turn_flow`` event, plus
the optional ``on_turn_flow`` callback) — observability is not opt-in — and, by
default, narrates each turn in the background: its own backend refines the
diagram into a dev-facing account that supersedes the mechanical one. A turn that
crashes still gets a diagram; a raising callback never breaks the turn; an
invalid narration is rejected and the mechanical diagram is kept.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from fi_runner import (
    BackendError,
    FlowNarrationError,
    FlowNarrator,
    MutationStage,
    Runner,
    ToolCall,
    TurnResult,
    events_to_mermaid,
    narrate_flow,
    triage_guard,
)

_NARRATION_MARKER = "annotating one of your OWN"  # present in the narration system prompt


@dataclass
class _FakeBackend:
    """Echoes a fixed reply. As a narrator it returns a non-flowchart (so default
    narration is rejected), keeping these tests focused on the mechanical path."""

    text: str = "ok"
    usage: dict | None = None

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text=self.text, usage=self.usage)


@dataclass
class _BoomBackend:
    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        raise RuntimeError("model unreachable")


@dataclass
class _NarratingBackend:
    """Replies normally to a turn, and returns a VALID enriched diagram (wrapped
    in a ```mermaid fence, preserving the request_id anchor) when asked to
    narrate. Records how many narration calls it received."""

    text: str = "respuesta clínica"
    narration_calls: int = field(default=0)

    async def run_turn(self, *, system_prompt: str, user_message: str, **kwargs) -> TurnResult:  # noqa: ANN003
        if _NARRATION_MARKER in system_prompt:
            self.narration_calls += 1
            rid = (re.search(r"request_id=([\w-]+)", user_message) or [None, "?"])[1]
            return TurnResult(
                text=(
                    "```mermaid\n"
                    "flowchart TD\n"
                    f'    start(["run · request_id={rid}"])\n'
                    '    why["reasoning: prioricé seguridad — detecté señal de crisis"]\n'
                    "    start --> why\n"
                    "    classDef crit fill:#fdd,stroke:#c00;\n"
                    "    class why crit;\n"
                    "```"
                )
            )
        return TurnResult(text=self.text)


def _flow_sink() -> tuple[list[tuple[str, str]], Callable[[str, str], None]]:
    flows: list[tuple[str, str]] = []
    return flows, lambda rid, mermaid: flows.append((rid, mermaid))


def _event_sink() -> tuple[list[tuple[str, dict]], Callable[[str, dict], None]]:
    events: list[tuple[str, dict]] = []
    return events, lambda e, f: events.append((e, f))


# --- pure renderer ------------------------------------------------------------


def test_events_to_mermaid_renders_skeleton_and_completion():
    events = [
        (
            "turn_completed",
            {
                "request_id": "r1",
                "model": "m1",
                "latency_ms": 12.3,
                "tokens": {"output_tokens": 7, "total_cost_usd": 0.0012},
                "mcp_count": 2,
                "attempts": 1,
                "guard_levels": {"triage": "CRITICAL"},
            },
        ),
        ("guard_critical", {"guard": "triage", "request_id": "r1", "level": "CRITICAL"}),
    ]
    mmd = events_to_mermaid(events, title="t")
    assert mmd.startswith("flowchart TD")
    assert "request_id=r1" in mmd
    assert "2 MCP server(s)" in mmd
    assert "guard: triage → CRITICAL" in mmd
    assert "12.3 ms" in mmd and "7 out tok" in mmd and "$0.0012" in mmd
    assert "class g0 crit;" in mmd  # the CRITICAL guard node is highlighted


def test_events_to_mermaid_failed_turn_has_error_node_no_completion():
    events = [("backend_error", {"backend": "BoomBackend", "model": "m1", "attempt": 1})]
    mmd = events_to_mermaid(events, title="failed")
    assert "backend_error<br/>BoomBackend" in mmd
    assert "backend -.raises.-> berr" in mmd
    assert "turn_completed" not in mmd  # no completion node on a crash


def test_events_to_mermaid_renders_tool_nodes_chained_after_backend():
    events = [
        ("tool_called", {"index": 0, "name": "mcp__cognitive__assess", "server": "cognitive", "is_error": False}),
        ("tool_called", {"index": 1, "name": "Bash", "server": None, "is_error": True}),
        ("turn_completed", {"request_id": "r1", "mcp_count": 1, "attempts": 1, "guard_levels": {}}),
    ]
    mmd = events_to_mermaid(events)
    assert "tool: mcp__cognitive__assess" in mmd and "tool: Bash" in mmd
    assert "backend --> tool0" in mmd and "tool0 --> tool1" in mmd  # chained in order
    assert "class tool1 err;" in mmd  # the failed tool is highlighted


# --- mechanical diagram: always published -------------------------------------


@pytest.mark.asyncio
async def test_turn_flow_event_always_emitted_even_without_callback():
    # Observability is not opt-in: a turn_flow event fires with no on_turn_flow
    # set. flow_narrator=None isolates the mechanical path.
    events, event_sink = _event_sink()
    runner = Runner(backend=_FakeBackend("hola"), persona="p", on_event=event_sink, flow_narrator=None)
    await runner.run("hi", request_id="t-1")
    flow = [f for e, f in events if e == "turn_flow"]
    assert len(flow) == 1
    assert flow[0]["request_id"] == "t-1"
    assert flow[0]["narrated"] is False
    assert flow[0]["mermaid"].startswith("flowchart TD")


@pytest.mark.asyncio
async def test_on_turn_flow_callback_gets_mechanical_diagram():
    flows, flow_sink = _flow_sink()
    runner = Runner(
        backend=_FakeBackend("hola"), persona="p", on_turn_flow=flow_sink, flow_narrator=None
    )
    await runner.run("hi", request_id="t-1")
    await runner.run("hi again", request_id="t-2")
    assert [rid for rid, _ in flows] == ["t-1", "t-2"]
    assert all("flowchart TD" in mmd for _, mmd in flows)


@pytest.mark.asyncio
async def test_mechanical_flow_reflects_guards_and_post_processors():
    flows, flow_sink = _flow_sink()
    runner = Runner(
        backend=_FakeBackend("  el paciente refiere plan suicida  "),
        persona="p",
        guards=[triage_guard("psychiatry")],
        post_processors=[MutationStage(name="strip", apply=lambda t, c: t.strip(), max_shrink_pct=None)],
        on_turn_flow=flow_sink,
        flow_narrator=None,
    )
    await runner.run("hola doc", request_id="t-clinical")
    _, mmd = flows[0]
    assert "guard: triage → CRITICAL" in mmd
    assert "post: strip" in mmd
    assert "crit;" in mmd


@pytest.mark.asyncio
async def test_runner_emits_tool_trace_phi_safe_and_diagram_shows_tools():
    @dataclass
    class _ToolBackend:
        async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
            return TurnResult(
                text="ok",
                tool_calls=[
                    ToolCall.make("mcp__cognitive__assess", input={"q": "phi"}, is_error=False),
                    ToolCall.make("Bash", input={"command": "ls"}, is_error=True),
                ],
            )

    events, event_sink = _event_sink()
    flows, flow_sink = _flow_sink()
    runner = Runner(
        backend=_ToolBackend(), persona="p", on_event=event_sink, on_turn_flow=flow_sink, flow_narrator=None
    )
    await runner.run("hi", request_id="t-tools")
    tool_events = [f for e, f in events if e == "tool_called"]
    assert [t["name"] for t in tool_events] == ["mcp__cognitive__assess", "Bash"]
    assert tool_events[0]["server"] == "cognitive" and tool_events[1]["is_error"] is True
    assert "input" not in tool_events[0]  # PHI-safe: tool input never reaches telemetry
    assert [f for e, f in events if e == "turn_completed"][0]["tool_count"] == 2
    _, mmd = flows[0]
    assert "tool: mcp__cognitive__assess" in mmd and "tool: Bash" in mmd


@pytest.mark.asyncio
async def test_failed_turn_still_publishes_flow():
    events, event_sink = _event_sink()
    runner = Runner(backend=_BoomBackend(), persona="p", on_event=event_sink, flow_narrator=None)
    with pytest.raises(BackendError):
        await runner.run("hi", request_id="t-boom")
    flow = [f for e, f in events if e == "turn_flow"]
    assert len(flow) == 1  # the finally path published the crashed turn's diagram
    assert "backend_error" in flow[0]["mermaid"]


@pytest.mark.asyncio
async def test_raising_on_turn_flow_never_breaks_turn():
    events, event_sink = _event_sink()

    def boom_flow(_rid: str, _mmd: str) -> None:
        raise ValueError("disk full")

    runner = Runner(
        backend=_FakeBackend("hola"),
        persona="p",
        on_event=event_sink,
        on_turn_flow=boom_flow,
        flow_narrator=None,
    )
    result = await runner.run("hi", request_id="t-safe")
    assert result.text == "hola"  # turn returns normally despite the callback raising
    flow_errors = [f for e, f in events if e == "turn_flow_error"]
    assert len(flow_errors) == 1
    assert flow_errors[0]["request_id"] == "t-safe"


# --- LLM narration (the INSIDE view, on by default) ---------------------------


@pytest.mark.asyncio
async def test_narration_on_by_default_supersedes_mechanical():
    flows, flow_sink = _flow_sink()
    events, event_sink = _event_sink()
    backend = _NarratingBackend()
    # No flow_narrator arg → narration is ON by default.
    async with Runner(backend=backend, persona="p", on_turn_flow=flow_sink, on_event=event_sink) as runner:
        await runner.run("hola doc", request_id="t-narrate")
    # aclose() (via the context manager) drained the background narration.
    assert backend.narration_calls == 1  # the second, narration backend call happened
    # on_turn_flow fired twice: mechanical first, narrated second (latest wins).
    assert [rid for rid, _ in flows] == ["t-narrate", "t-narrate"]
    mechanical, narrated = flows[0][1], flows[1][1]
    assert "reasoning: prioricé seguridad" in narrated and "reasoning" not in mechanical
    assert "request_id=t-narrate" in narrated  # anchor preserved
    # both a mechanical (narrated=False) and a narrated (narrated=True) event fired
    narrated_flags = sorted(f["narrated"] for e, f in events if e == "turn_flow")
    assert narrated_flags == [False, True]


@pytest.mark.asyncio
async def test_invalid_narration_rejected_keeps_mechanical():
    flows, flow_sink = _flow_sink()
    events, event_sink = _event_sink()
    # _FakeBackend's narration reply is "ok" — not a flowchart → rejected.
    async with Runner(
        backend=_FakeBackend("hola"), persona="p", on_turn_flow=flow_sink, on_event=event_sink
    ) as runner:
        await runner.run("hi", request_id="t-bad")
    assert [rid for rid, _ in flows] == ["t-bad"]  # only the mechanical diagram
    assert [f["request_id"] for e, f in events if e == "flow_narration_error"] == ["t-bad"]


@pytest.mark.asyncio
async def test_flow_narrator_none_skips_second_backend_call():
    backend = _NarratingBackend()
    events, event_sink = _event_sink()
    async with Runner(
        backend=backend, persona="p", on_event=event_sink, flow_narrator=None
    ) as runner:
        await runner.run("hi", request_id="t-off")
    assert backend.narration_calls == 0  # no narration → no second call
    assert not [e for e, _ in events if e == "turn_flow" and _ and _.get("narrated")]


@pytest.mark.asyncio
async def test_custom_narrator_model_override():
    seen_models: list[str | None] = []

    @dataclass
    class _ModelSpyBackend:
        async def run_turn(self, *, system_prompt: str, model: str | None = None, **kwargs) -> TurnResult:  # noqa: ANN003
            if _NARRATION_MARKER in system_prompt:
                seen_models.append(model)
                return TurnResult(text='flowchart TD\n    start(["run · request_id=t-mod"])')
            return TurnResult(text="reply")

    async with Runner(
        backend=_ModelSpyBackend(),
        persona="p",
        model="big-model",
        flow_narrator=FlowNarrator(model="cheap-narrator"),
    ) as runner:
        await runner.run("hi", request_id="t-mod")
    assert seen_models == ["cheap-narrator"]  # narrator model overrode the turn model


# --- standalone narrate_flow --------------------------------------------------


@pytest.mark.asyncio
async def test_narrate_flow_strips_fences_and_validates_anchor():
    mechanical = events_to_mermaid(
        [("turn_completed", {"request_id": "r9", "mcp_count": 0, "attempts": 1, "guard_levels": {}})]
    )
    refined = await narrate_flow(
        _NarratingBackend(),
        mechanical,
        user_message="u",
        response_text="r",
        request_id="r9",
    )
    assert refined.startswith("flowchart TD")  # ```mermaid fence stripped
    assert "request_id=r9" in refined


@pytest.mark.asyncio
async def test_narrate_flow_rejects_non_flowchart():
    with pytest.raises(FlowNarrationError, match="flowchart"):
        await narrate_flow(_FakeBackend("just prose, no diagram"), "flowchart TD", user_message="u", response_text="r")


@pytest.mark.asyncio
async def test_narrate_flow_rejects_dropped_anchor():
    @dataclass
    class _AnchorlessBackend:
        async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
            return TurnResult(text='flowchart TD\n    a["no anchor here"]')

    with pytest.raises(FlowNarrationError, match="anchor"):
        await narrate_flow(
            _AnchorlessBackend(), "flowchart TD", user_message="u", response_text="r", request_id="rX"
        )
