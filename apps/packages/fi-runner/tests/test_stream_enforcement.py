"""run_stream enforces what run() enforces — the two paths share one attempt loop.

The defect these tests pin: the retry budget, the guard verdict and the
plan-guard veto lived only inside ``run()``'s private loop, while every consumer
of this framework calls ``run_stream()``. So a runner could declare an
``AntiDriftGuard`` and stream the un-sanitized text to the user anyway, with the
cleaned version arriving afterwards in the result frame and the docstring telling
the consumer to "reconcile on result". A guard cannot enforce what has already
been delivered.

The fix is :meth:`Runner._attempt_stream`, drained by both entrypoints. These
tests assert the two halves of the contract that follows from it:

  1. A runner that CAN still change its answer (guards / plan guard / retry
     budget) withholds text until it has settled.
  2. A runner that CANNOT — no guards, one attempt, which is every shipping
     consumer today — streams deltas live, byte-identical to before.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from fi_runner import (
    BackendError,
    GuardOutcome,
    RetryPolicy,
    Runner,
    ToolCall,
    TurnResult,
    plan_guard,
)


@dataclass
class _StreamBackend:
    """Streams two text deltas then a result. Records every system prompt it saw."""

    replies: list[str] = field(default_factory=lambda: ["hello"])
    calls: list[str] = field(default_factory=list)

    def _reply(self) -> str:
        return self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        self.calls.append(kwargs.get("system_prompt", ""))
        return TurnResult(text=self._reply())

    async def run_turn_stream(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs.get("system_prompt", ""))
        reply = self._reply()
        half = len(reply) // 2
        yield {"type": "text", "text": reply[:half]}
        yield {"type": "text", "text": reply[half:]}
        yield {"type": "result", "result": TurnResult(text=reply)}


@dataclass
class _PlanningBackend:
    """Declares a plan via the task_tracker MCP before answering."""

    steps: list[list[str]] = field(default_factory=lambda: [["rm -rf the corpus"], ["ask first"]])
    calls: list[str] = field(default_factory=list)

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        self.calls.append(kwargs.get("system_prompt", ""))
        return TurnResult(text="done")

    async def run_turn_stream(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs.get("system_prompt", ""))
        steps = self.steps[min(len(self.calls) - 1, len(self.steps) - 1)]
        yield {
            "type": "tool_call",
            "tool": ToolCall.make(
                "mcp__fi_core_task_tracker__declare_plan",
                input={"session_id": "s1", "steps": steps},
                id=f"t{len(self.calls)}",
            ),
        }
        yield {"type": "text", "text": "done"}
        yield {"type": "result", "result": TurnResult(text="done")}


@dataclass
class _ResultlessBackend:
    """A backend that ends its stream without ever emitting a result event."""

    async def run_turn(self, **kwargs) -> TurnResult:  # noqa: ANN003
        return TurnResult(text="unused")

    async def run_turn_stream(self, **kwargs):  # noqa: ANN003
        yield {"type": "text", "text": "half a thought"}


@dataclass
class _RedactingGuard:
    """Transformational guard: replaces the answer outright."""

    name: str = "redact"
    clean: str = "[redacted]"

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        return GuardOutcome(text_override=self.clean)


@dataclass
class _RetryOnceGuard:
    """Asks for exactly one retry, then accepts whatever comes back."""

    name: str = "retry_once"
    seen: int = 0

    def inspect(
        self, *, response_text: str, context: tuple[str, ...] = (), final: bool = False
    ) -> GuardOutcome:
        self.seen += 1
        if self.seen == 1 and not final:
            return GuardOutcome(retry=True, reinforcement="TRY HARDER")
        return GuardOutcome()


def _sink() -> tuple[list[tuple[str, dict]], Callable[[str, dict], None]]:
    events: list[tuple[str, dict]] = []
    return events, lambda e, f: events.append((e, f))


# --- 1. enforcement: nothing reaches the user before the guard has spoken -----


@pytest.mark.asyncio
async def test_a_transformational_guard_is_enforced_before_the_text_is_delivered():
    """The raw text must NEVER appear on the wire — not even as a delta later
    superseded by the result frame. This is the whole point of a guard."""
    runner = Runner(
        backend=_StreamBackend(replies=["the unsafe answer"]),
        persona="p",
        guards=[_RedactingGuard()],
        flow_narrator=None,
    )
    events = [ev async for ev in runner.run_stream("hi")]
    streamed = "".join(ev["text"] for ev in events if ev["type"] == "text")
    assert streamed == "[redacted]"
    assert "unsafe" not in streamed
    assert events[-1]["result"].text == "[redacted]"


@pytest.mark.asyncio
async def test_run_stream_retries_when_a_guard_asks_and_the_budget_allows():
    """Retry used to be run()-only ("the text is already streamed, so no retry").
    Withholding the text is what makes a second attempt possible."""
    backend = _StreamBackend(replies=["first try", "second try"])
    runner = Runner(
        backend=backend,
        persona="p",
        guards=[_RetryOnceGuard()],
        retry_policy=RetryPolicy(max_attempts=2),
        flow_narrator=None,
    )
    events = [ev async for ev in runner.run_stream("hi")]
    assert len(backend.calls) == 2, "the guard's retry request was ignored"
    assert "TRY HARDER" in backend.calls[1], "the reinforcement never reached the second attempt"
    streamed = "".join(ev["text"] for ev in events if ev["type"] == "text")
    assert streamed == "second try"
    assert "first try" not in streamed, "the abandoned attempt leaked to the user"


@pytest.mark.asyncio
async def test_a_rejected_plan_forces_another_attempt():
    """The plan veto was advisory: it emitted plan_rejected and let the turn run
    to completion anyway. With a retry budget it now costs the agent the attempt
    and its reinforcement reaches the next system prompt."""
    backend = _PlanningBackend()
    runner = Runner(
        backend=backend,
        persona="p",
        plan_guard=plan_guard(
            blocked_patterns=[r"rm\s+-rf"],
            reinforcement="NEVER propose a destructive step.",
        ),
        retry_policy=RetryPolicy(max_attempts=2),
        flow_narrator=None,
    )
    events = [ev async for ev in runner.run_stream("hi", session_id="s1")]
    assert any(ev["type"] == "plan_rejected" for ev in events)
    assert len(backend.calls) == 2, "the rejected plan cost the agent nothing"
    assert "NEVER propose a destructive step." in backend.calls[1]


@pytest.mark.asyncio
async def test_an_allowed_plan_does_not_burn_a_retry():
    backend = _PlanningBackend(steps=[["ask first"]])
    runner = Runner(
        backend=backend,
        persona="p",
        plan_guard=plan_guard(blocked_patterns=[r"rm\s+-rf"]),
        retry_policy=RetryPolicy(max_attempts=2),
        flow_narrator=None,
    )
    events = [ev async for ev in runner.run_stream("hi", session_id="s1")]
    assert not any(ev["type"] == "plan_rejected" for ev in events)
    assert len(backend.calls) == 1


@pytest.mark.asyncio
async def test_turn_completed_reports_the_attempts_actually_spent():
    events, sink = _sink()
    runner = Runner(
        backend=_StreamBackend(replies=["one", "two"]),
        persona="p",
        guards=[_RetryOnceGuard()],
        retry_policy=RetryPolicy(max_attempts=2),
        on_event=sink,
        flow_narrator=None,
    )
    _ = [ev async for ev in runner.run_stream("hi")]
    completed = [f for e, f in events if e == "turn_completed"][0]
    assert completed["attempts"] == 2, "a streamed turn always reported attempts=1"
    assert completed["streamed"] is True


# --- 2. regression: the shipping consumers must keep their live tokens --------


@pytest.mark.asyncio
async def test_a_runner_with_nothing_to_enforce_still_streams_live():
    """og118 and fenix declare no guards, no plan guard and one attempt. Their
    turns must stay byte-identical: two deltas, live, in order."""
    runner = Runner(backend=_StreamBackend(replies=["hola mundo"]), persona="p", flow_narrator=None)
    events = [ev async for ev in runner.run_stream("hi")]
    assert [ev["type"] for ev in events] == ["text", "text", "result"]
    assert [ev["text"] for ev in events if ev["type"] == "text"] == ["hola ", "mundo"]


@pytest.mark.asyncio
async def test_enforcement_is_decided_by_what_the_runner_declares():
    plain = Runner(backend=_StreamBackend(), persona="p", flow_narrator=None)
    assert plain._enforces_before_delivery is False
    for guarded in (
        Runner(backend=_StreamBackend(), persona="p", guards=[_RedactingGuard()], flow_narrator=None),
        Runner(backend=_StreamBackend(), persona="p", plan_guard=plan_guard(blocked_patterns=["x"]), flow_narrator=None),
        Runner(backend=_StreamBackend(), persona="p", retry_policy=RetryPolicy(max_attempts=2), flow_narrator=None),
    ):
        assert guarded._enforces_before_delivery is True


# --- 3. the contract that used to be an `assert` -----------------------------


@pytest.mark.asyncio
async def test_a_backend_that_never_settles_raises_instead_of_handing_back_none():
    """`assert result is not None` vanishes under `python -O`, and the runner
    then yielded result=None where its own contract promises a TurnResult."""
    runner = Runner(backend=_ResultlessBackend(), persona="p", flow_narrator=None)
    with pytest.raises(BackendError, match="without a result event"):
        _ = [ev async for ev in runner.run_stream("hi")]


# --- 4. observability is no longer run()-only --------------------------------


@pytest.mark.asyncio
async def test_a_streamed_turn_publishes_its_flow_diagram():
    """`on_turn_flow`'s own comment promised "observability is never opt-in"
    while run_stream produced no diagram at all — and run_stream is the only
    entrypoint anyone calls."""
    events, sink = _sink()
    diagrams: list[tuple[str, str]] = []
    runner = Runner(
        backend=_StreamBackend(),
        persona="p",
        on_event=sink,
        on_turn_flow=lambda rid, mermaid: diagrams.append((rid, mermaid)),
        flow_narrator=None,
    )
    _ = [ev async for ev in runner.run_stream("hi", request_id="s9")]
    flows = [f for e, f in events if e == "turn_flow"]
    assert flows and flows[0]["request_id"] == "s9"
    assert flows[0]["narrated"] is False
    assert diagrams and "flowchart" in diagrams[0][1].lower()


@pytest.mark.asyncio
async def test_a_crashed_stream_still_publishes_its_diagram():
    events, sink = _sink()
    runner = Runner(backend=_ResultlessBackend(), persona="p", on_event=sink, flow_narrator=None)
    with pytest.raises(BackendError):
        _ = [ev async for ev in runner.run_stream("hi")]
    assert any(e == "turn_flow" for e, _ in events), "a failed turn's path is as useful as a clean one"
