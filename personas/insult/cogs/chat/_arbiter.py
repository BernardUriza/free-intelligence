"""The DeMux arbiter — supervise a runner turn instead of a blind read timeout.

A flat 120s read timeout treated a runner that was merely SLOW (a legitimate long
research turn) as DOWN and handed the turn to ALICE (2026-07-10 incident: Insult's
research times escalated 26→64→111→120s and the fourth was failed over even though
the runner never died). The arbiter watches the turn like a referee: it grants the
gpt-4.1-estimated budget, and past it probes the runner's ``/health`` — a runner
still answering is EXTENDED (let it keep working); only a runner that stops
answering (``max_health_strikes`` consecutive unreachable probes) or the absolute
``hard_cap_s`` ends the turn, as a ``RunnerDownError`` the caller's existing
failover/degradation path already handles.

See ``_stage_call_llm`` (the consumer) and the ``glistening-purring-snail`` plan.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from khimeras_shared.runner.agent_client import RunnerDownError

log = structlog.get_logger()


async def _cancel_and_swallow(task: asyncio.Task) -> None:
    """Cancel an in-flight chat task and absorb whatever it raises. The runner may
    keep processing on its side (we can't recall the request), but the plumbing is
    done waiting — a re-POST would double-spend the turn, so we just let go."""
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, Exception):
        await task


async def supervise_runner_turn(
    chat_task: asyncio.Task[Any],
    *,
    budget_s: float,
    hard_cap_s: float,
    checkpoint_s: float,
    health_probe: Callable[[], Awaitable[dict]],
    on_budget_exceeded: Callable[[], Awaitable[None]] | None = None,
    max_health_strikes: int = 2,
) -> Any:
    """Supervise a runner turn already in flight as ``chat_task``.

    Returns the task's result if it finishes within the extended window. Raises
    ``RunnerDownError`` when the runner stops answering ``/health`` for
    ``max_health_strikes`` consecutive probes, or when ``hard_cap_s`` is reached —
    so the caller's failover/degradation path handles a genuinely-down brain. Any
    exception the task raises on its own (a 4xx ``PersonaTurnError``, a
    connect-exhausted ``RunnerDownError``) propagates unchanged."""
    start = time.monotonic()

    # Phase 1 — wait up to the estimated budget for a normal completion.
    done, _ = await asyncio.wait({chat_task}, timeout=budget_s)
    if chat_task in done:
        return chat_task.result()

    # Budget exceeded: the runner is taking longer than estimated. Tell the user
    # once ("sigo en ello") and switch to referee mode — extend while it lives.
    if on_budget_exceeded is not None:
        try:
            await on_budget_exceeded()
        except Exception:
            log.exception("arbiter_on_budget_exceeded_failed")

    strikes = 0
    while True:
        remaining = hard_cap_s - (time.monotonic() - start)
        if remaining <= 0:
            log.warning("arbiter_hard_cap_reached", hard_cap_s=hard_cap_s)
            await _cancel_and_swallow(chat_task)
            raise RunnerDownError(f"arbiter: hard cap {hard_cap_s}s reached")

        done, _ = await asyncio.wait({chat_task}, timeout=min(checkpoint_s, remaining))
        if chat_task in done:
            log.info("arbiter_extended_turn_completed", elapsed_s=round(time.monotonic() - start, 1))
            return chat_task.result()

        # Checkpoint — is the runner still alive? A probe that raises is treated
        # as unreachable (fail toward intervention, never hang on a broken probe).
        try:
            health = await health_probe()
        except Exception:
            log.exception("arbiter_health_probe_failed")
            health = {"status": "unreachable", "error": "probe raised"}
        if health.get("status") != "unreachable":
            strikes = 0
            log.info(
                "arbiter_extend",
                elapsed_s=round(time.monotonic() - start, 1),
                health=health.get("status"),
            )
            continue
        strikes += 1
        log.warning("arbiter_health_strike", strikes=strikes, max_strikes=max_health_strikes)
        if strikes >= max_health_strikes:
            await _cancel_and_swallow(chat_task)
            raise RunnerDownError(f"arbiter: runner /health unreachable ({strikes} strikes)")


__all__ = ["supervise_runner_turn"]
