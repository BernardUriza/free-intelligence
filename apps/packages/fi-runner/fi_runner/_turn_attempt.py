"""One backend attempt of a turn, as a stream of events.

The retry loop lives in :meth:`fi_runner.Runner._attempt_stream`; this module is
what a single pass through the backend does: normalize a one-shot backend into
the streaming shape, withhold or forward text, derive plan events from
``task_tracker`` calls and let the plan guard veto a declared plan.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from ._plan_events import _derive_plan_events, _PlanStreamObserver
from .backend import TurnResult
from .plan_guard import PlanGuard


@dataclass
class AttemptOutcome:
    """What one attempt left behind once its stream is drained."""

    result: TurnResult | None = None
    plan_reinforcement: str = ""


async def backend_events(backend: Any, **turn: Any) -> AsyncIterator[dict[str, Any]]:
    """Stream one backend turn; a backend without ``run_turn_stream`` yields one result event."""
    if hasattr(backend, "run_turn_stream"):
        async for event in backend.run_turn_stream(**turn):
            yield event
        return
    yield {"type": "result", "result": await backend.run_turn(**turn)}


def plan_veto(plan_guard: PlanGuard | None, derived: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    """The ``plan_rejected`` event for a declared plan the guard refuses, else ``None``."""
    if plan_guard is None or derived.get("type") != "plan":
        return None
    steps = (derived.get("data") or {}).get("steps") or []
    outcome = plan_guard.inspect(steps)
    if outcome.allowed:
        return None
    return {"type": "plan_rejected", "data": {
        "request_id": request_id,
        "reason": outcome.reason,
        "matched": list(outcome.matched),
        "reinforcement": outcome.reinforcement,
        "guard": plan_guard.name,
    }}


async def stream_attempt(
    backend: Any,
    turn: dict[str, Any],
    outcome: AttemptOutcome,
    *,
    live_text: bool,
    plan_guard: PlanGuard | None,
    session_id: str | None,
    request_id: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield one attempt's events and record its result and plan veto on ``outcome``.

    Text deltas are dropped when ``live_text`` is false: the caller delivers the
    settled text after guards run. Tool-call and plan events are always live.
    """
    # Per attempt: a retried turn declares a fresh plan with fresh step counters.
    observer = _PlanStreamObserver()
    async for event in backend_events(backend, **turn):
        kind = event.get("type")
        if kind == "result":
            outcome.result = event["result"]
            continue
        if kind == "text":
            if live_text:
                yield event
            continue
        yield event
        if kind != "tool_call":
            continue
        for derived in _derive_plan_events(
            event["tool"], session_id=session_id, request_id=request_id, observer=observer
        ):
            yield derived
            rejected = plan_veto(plan_guard, derived, request_id)
            if rejected is not None:
                yield rejected
                outcome.plan_reinforcement = rejected["data"]["reinforcement"] or ""
