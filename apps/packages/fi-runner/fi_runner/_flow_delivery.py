"""Flow diagram delivery + background narration — observability primitives.

EVERY turn self-documents in Free Intelligence (observability is never
opt-in). The Runner collects telemetry events during the turn and, once it
settles or crashes, renders a Mermaid flowchart of the path taken — first
the MECHANICAL diagram (rendered from raw events), then optionally a
NARRATED refinement from the backend itself (the INSIDE view).

This module is the helper layer for that flow:

  - :func:`deliver_turn_flow` — render + emit the mechanical diagram, hand
    it to the optional ``on_turn_flow`` callback, all guarded so a render
    or callback failure can never mask the turn's own outcome.
  - :func:`schedule_narration` — fire-and-track a background narration task.
  - :func:`narrate_and_publish` — the body of that background task: ask the
    backend to refine, publish the narrated diagram superseding the
    mechanical one.
  - :func:`drain_narrations` — await the tracked pool on shutdown so no
    narration is silently lost (the closing half of ``schedule_narration``).

All functions are RUNNER-AGNOSTIC — they take the few pieces of state they
need as arguments (emit sink, backend, narrator, callback). The Runner
class wires them together; the heavy lifting lives here."""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from .backend import AgentBackend
from .flow import Event, events_to_mermaid
from .narrate import narrate_flow
from ._runner_config import FlowNarrator


# Type aliases used both here and by the Runner. Kept loose (Any-friendly)
# to avoid coupling — the consumer's emit sink can be anything callable.
EmitSink = Callable[[str, dict[str, Any]], None]
TurnFlowCallback = Callable[[str, str], None]


def deliver_turn_flow(
    request_id: str,
    events: list[Event],
    *,
    emit: EmitSink,
    on_turn_flow: TurnFlowCallback | None,
) -> None:
    """Publish this turn's MECHANICAL flow diagram: always as a ``turn_flow``
    telemetry event (observability is never opt-in) and — when set — to
    ``on_turn_flow``. Defensive: a render/callback error is reported as
    ``turn_flow_error`` and swallowed — a diagram is never a turn's SPOF."""
    try:
        mermaid = events_to_mermaid(events, title=f"fi_runner turn · {request_id}")
    except Exception as exc:  # noqa: BLE001 - a diagram is never a turn's SPOF
        emit("turn_flow_error", {"request_id": request_id, "error": str(exc)})
        return
    emit("turn_flow", {"request_id": request_id, "narrated": False, "mermaid": mermaid})
    _call_turn_flow(request_id, mermaid, emit=emit, on_turn_flow=on_turn_flow)


def _call_turn_flow(
    request_id: str,
    mermaid: str,
    *,
    emit: EmitSink,
    on_turn_flow: TurnFlowCallback | None,
) -> None:
    """Hand a diagram to the optional ``on_turn_flow`` callback, guarded so a
    raising consumer can never break (or mask) the turn."""
    if on_turn_flow is None:
        return
    try:
        on_turn_flow(request_id, mermaid)
    except Exception as exc:  # noqa: BLE001 - a diagram is never a turn's SPOF
        emit("turn_flow_error", {"request_id": request_id, "error": str(exc)})


def schedule_narration(
    request_id: str,
    events: list[Event],
    user_message: str,
    response_text: str,
    model: str | None,
    *,
    narrator: FlowNarrator,
    backend: AgentBackend,
    emit: EmitSink,
    on_turn_flow: TurnFlowCallback | None,
    task_pool: set[asyncio.Task[None]],
) -> None:
    """Fire the turn's narration in the background and track the task so
    ``aclose()`` can drain it — a narration is never silently lost.

    Backpressure: when ``task_pool`` is already at
    ``narrator.max_inflight_narrations``, the narration is DROPPED and a
    ``narration_dropped`` event is emitted. This bounds the task set so a
    slow narration backend + burst of turns can't grow the pool without
    limit (R5). The mechanical diagram still ships — only the
    narrated refinement is skipped for this turn."""
    if len(task_pool) >= narrator.max_inflight_narrations:
        emit("narration_dropped", {
            "request_id": request_id,
            "inflight": len(task_pool),
            "max_inflight": narrator.max_inflight_narrations,
            "reason": "narration_pool_saturated",
        })
        return
    task = asyncio.create_task(narrate_and_publish(
        request_id, events, user_message, response_text, model,
        narrator=narrator, backend=backend,
        emit=emit, on_turn_flow=on_turn_flow,
    ))
    task_pool.add(task)
    task.add_done_callback(task_pool.discard)


async def narrate_and_publish(
    request_id: str,
    events: list[Event],
    user_message: str,
    response_text: str,
    model: str | None,
    *,
    narrator: FlowNarrator,
    backend: AgentBackend,
    emit: EmitSink,
    on_turn_flow: TurnFlowCallback | None,
) -> None:
    """Ask the backend to refine this turn's flow into a dev-facing narrative,
    then publish it (a ``turn_flow`` event with ``narrated=True`` + the
    ``on_turn_flow`` callback), superseding the mechanical diagram. Best
    effort: any failure emits ``flow_narration_error`` and keeps the already
    published mechanical diagram."""
    mechanical = events_to_mermaid(events, title=f"fi_runner turn · {request_id}")
    try:
        refined = await narrate_flow(
            backend,
            mechanical,
            user_message=user_message,
            response_text=response_text,
            model=narrator.model or model,
            instructions=narrator.instructions,
            request_id=request_id,
        )
    except Exception as exc:  # noqa: BLE001 - narration is best-effort observability
        emit("flow_narration_error", {"request_id": request_id, "error": str(exc)})
        return
    emit("turn_flow", {"request_id": request_id, "narrated": True, "mermaid": refined})
    _call_turn_flow(request_id, refined, emit=emit, on_turn_flow=on_turn_flow)


async def drain_narrations(
    task_pool: set["asyncio.Task[None]"],
    *,
    emit: EmitSink,
) -> None:
    """Await every in-flight narration so none is lost on shutdown.

    ``return_exceptions=True`` is required so one failed narration doesn't
    cancel the others mid-drain. Every failure is surfaced as a
    ``narration_drain_error`` event — otherwise narrations that raised would
    be silently swallowed by gather (a documented asyncio footgun).
    ``BaseException`` (not ``Exception``) catches ``CancelledError`` too —
    gather's ``return_exceptions`` does not auto-detect it via ``Exception``."""
    if not task_pool:
        return
    results = await asyncio.gather(*tuple(task_pool), return_exceptions=True)
    for r in results:
        if isinstance(r, BaseException):
            emit("narration_drain_error", {
                "error_type": type(r).__name__,
                "error": str(r),
            })


__all__ = [
    "EmitSink",
    "TurnFlowCallback",
    "deliver_turn_flow",
    "schedule_narration",
    "narrate_and_publish",
    "drain_narrations",
]
