"""Typed failure model + safe Discord I/O helpers for the turn pipeline.

Pre-PR2 the turn handler had three structural defects that the
2026-05-08T23:59 outage exposed:

1. ``async with channel.typing(): await llm.chat(...)`` — ``Typing.__aenter__``
   makes a blocking HTTP request to ``POST /channels/{id}/typing``. When
   the channel is hot, that request 429-s with code 40062
   (``ServiceResourceIsBeingRateLimited``) and the exception kills the
   *entire* turn, including the LLM call that never ran. See
   discord.py ``context_managers.py:54-92``.

2. The ``except Exception`` log emitted ``chat_llm_failed`` even when the
   LLM was never invoked. The event name lied. There was no
   ``failure_stage`` field to disambiguate.

3. The recovery ``await message.channel.send(get_error_response(...))``
   ran on the same rate-limited channel without an inner ``try/except``.
   It silently re-raised, the exception bubbled past the handler, and
   the user saw nothing — not even an in-character error.

This module provides the contract + helpers to close all three:

- ``FailureClass`` / ``StageFailure`` give logs a typed, queryable
  shape so KQL can ``project failure_stage, failure_class`` instead
  of regex-extracting from ``chat_llm_failed`` strings.
- ``emit_typing_safe`` decouples the typing indicator from the LLM
  call: typing now lives as a fire-and-forget background task that
  swallows its own ``HTTPException`` and logs a structured warning
  instead of cancelling the turn.
- ``send_with_reaction_fallback`` guarantees the user always gets
  *some* signal — text if possible, a reaction if the channel is
  rate-limited (reactions live on a different bucket and almost
  always survive 40062), silence as the last resort.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum

import discord
import structlog

log = structlog.get_logger()


class Criticality(Enum):
    """How the orchestrator treats a stage's failure.

    - ``BUSINESS``: inline, sequential. A failure aborts the turn and
      surfaces ``chat_turn_failed`` with a typed failure_stage. The user
      sees an in-character error (or a reaction fallback).
    - ``COSMETIC``: inline, sequential. A failure is logged but the
      pipeline continues. Used for telemetry stages whose output is
      nice-to-have but whose absence does not invalidate the response.
    - ``BACKGROUND``: fire-and-forget via the cog's task spawner. The
      orchestrator does not wait. Used for typing indicators, post-
      delivery fact extraction, etc. — anything cosmetic that
      MUST NOT contend with the critical path for latency.
    """

    BUSINESS = "business"
    COSMETIC = "cosmetic"
    BACKGROUND = "background"


@dataclass(frozen=True)
class StageStop(Exception):  # noqa: N818 — "Stop" is the semantic, not an error
    """Short-circuit the pipeline with a non-failure outcome.

    Used by stages that decide the turn is intentionally over before
    reaching ``Deliver`` — e.g. ``EnsureNotTrivial`` raising
    ``StageStop("trivial_skipped")`` when ``is_trivial(text)`` returns
    True. The orchestrator catches this, logs no error, and returns
    the ``outcome`` to ``chat_turn_end`` as-is.

    Distinct from ``StageFailure``: ``StageStop`` is "everything went
    correctly, the answer is that we don't run the LLM here".
    """

    outcome: str

    def __str__(self) -> str:
        return f"StageStop({self.outcome})"


# Reaction the bot uses when text delivery fails — short, in-character,
# uses a different rate-limit bucket than channel.send.
_OVERLOADED_REACTION = "⏳"


class FailureClass(Enum):
    """Typed failure categories. Surfaces in ``chat_turn_failed`` logs and
    drives operator UX (Discord 429 vs LLM crash → very different
    runbook responses)."""

    DISCORD_THROTTLED = "discord_throttled"  # 429, including code 40062
    DISCORD_HTTP = "discord_http"  # other Discord 4xx/5xx
    LLM_FAILED = "llm_failed"  # Anthropic SDK exhaustion
    LLM_BAD_REQUEST = "llm_bad_request"  # Anthropic 400 (prompt issue)
    CONTEXT_FAILED = "context_failed"  # memory/context build failure
    UNEXPECTED = "unexpected"  # uncategorized — investigate


class FailoverReason(Enum):
    """Why a turn could not be served by its primary backend — the typed
    distinction PR-4b slice 2 introduced so the failover decision and the
    logs stop lying about what actually broke.

    - ``RUNNER_DOWN``: the persona-runner process is unreachable (connect
      refused / read timeout / 5xx). Insult's Claude brain is genuinely
      down, so a sibling persona on a DIFFERENT provider (ALICE on Azure
      OpenAI) may legitimately take the turn.
    - ``PERSONA_ERROR``: the runner answered but rejected THIS turn (4xx /
      invalid JSON). The brain is alive; failing over to ALICE would
      fabricate a 'fake ALICE'. Degrade honestly instead.
    - ``ROUTER_ERROR``: the demux host router (gpt-4.1) itself failed while
      classifying / routing. Reserved for when the live host router is wired
      into the turn path (later slice); the type exists now so the taxonomy
      is complete and greppable.
    - ``UNKNOWN``: anything uncategorized — investigate, never silently
      failover.
    """

    RUNNER_DOWN = "runner_down"
    PERSONA_ERROR = "persona_error"
    ROUTER_ERROR = "router_error"
    UNKNOWN = "unknown"


def classify_failover_reason(exc: BaseException) -> FailoverReason:
    """Map a turn-backend exception onto a ``FailoverReason``.

    ``RunnerDownError`` / ``PersonaTurnError`` are matched by isinstance (a
    cheap import from ``khimeras_shared``). The host router error is matched
    by class name so this hot-path module never has to import
    ``demux_ai.host_llm`` (which pulls in the heavy ``fi_runner`` backend);
    the host router is not wired into the turn path yet, so a name match is
    sufficient and keeps the boundary clean."""
    from khimeras_shared.runner.agent_client import PersonaTurnError, RunnerDownError

    if isinstance(exc, RunnerDownError):
        return FailoverReason.RUNNER_DOWN
    if isinstance(exc, PersonaTurnError):
        return FailoverReason.PERSONA_ERROR
    if type(exc).__name__ == "HostRouterError":
        return FailoverReason.ROUTER_ERROR
    return FailoverReason.UNKNOWN


@dataclass(frozen=True)
class FailoverDecision:
    """The pure outcome of classifying a turn-backend failure: WHY it failed
    and WHETHER a real sibling-persona failover may be attempted. Carries no
    I/O — the stage performs the actual ALICE invite / honest degradation
    based on this."""

    reason: FailoverReason
    attempt_alice: bool


def decide_failover(exc: BaseException, *, backend: str, alice_failover_enabled: bool) -> FailoverDecision:
    """Pure failover policy. A sibling-persona (ALICE) failover is attempted
    ONLY when the runner process is genuinely DOWN — never for a persona-turn
    error (that would fabricate a 'fake ALICE'), never when failover is
    disabled, never for a non-agent backend. The honest-degradation path is
    the caller's responsibility whenever ``attempt_alice`` is False OR the
    real ALICE invite is rejected."""
    reason = classify_failover_reason(exc)
    attempt_alice = alice_failover_enabled and backend == "agent_runner" and reason is FailoverReason.RUNNER_DOWN
    return FailoverDecision(reason=reason, attempt_alice=attempt_alice)


@dataclass
class StageFailure(Exception):  # noqa: N818 — explicit "Failure" suffix replaces "Error"
    """Structured failure surfaced from a stage. Carrying it as an
    exception keeps the existing control-flow patterns (``raise`` to
    abort the turn) while adding typed fields the orchestrator emits
    on ``chat_turn_failed``.

    The orchestrator catches ``StageFailure`` specifically, logs the
    typed event, attempts the in-character user notice via
    ``send_with_reaction_fallback``, and returns the outcome string
    that ``chat_turn_end`` expects.
    """

    stage: str  # "typing" | "llm_call" | "delivery" | "context" | ...
    failure_class: FailureClass
    error_type: str  # type(e).__name__
    error_msg: str  # str(e)[:200]
    elapsed_ms: int

    def __str__(self) -> str:
        return f"{self.stage}/{self.failure_class.value}: {self.error_type}: {self.error_msg}"


def classify_discord_exception(e: BaseException) -> FailureClass:
    """Map a Discord ``HTTPException`` to a ``FailureClass``. Returns
    ``DISCORD_THROTTLED`` for 429 (including code 40062), ``DISCORD_HTTP``
    for any other Discord HTTP error, ``UNEXPECTED`` otherwise."""
    if isinstance(e, discord.HTTPException):
        status = getattr(e, "status", None)
        code = getattr(e, "code", None)
        if status == 429 or code == 40062:
            return FailureClass.DISCORD_THROTTLED
        return FailureClass.DISCORD_HTTP
    return FailureClass.UNEXPECTED


async def emit_typing_safe(channel: discord.abc.Messageable) -> None:
    """Fire one ``send_typing`` call and swallow rate-limit errors.

    Replaces ``async with channel.typing():`` in the critical path. The
    context-manager form re-fires every 5s in a background loop; that's
    what makes it dangerous when a channel is hot, because each refresh
    is another request against the throttled bucket. A single one-shot
    send is enough to give the user a "thinking" indicator for ~10s,
    and if even that one shot 429-s we degrade silently — the user can
    still see the eventual reply.

    Caller is expected to ``asyncio.create_task`` this and NOT await
    it in the turn's critical path. If the task is awaited, the LLM
    call regains the original failure mode where typing 429 cancels
    the turn.
    """
    send_typing = getattr(channel, "_state", None)
    if send_typing is None or not hasattr(channel, "id"):
        return
    try:
        # Discord.py exposes the low-level typing trigger via the
        # underlying http client. Channel.typing() is the high-level
        # context manager — we want the one-shot underneath it.
        await channel._state.http.send_typing(channel.id)  # type: ignore[attr-defined]
    except discord.HTTPException as e:
        log.warning(
            "discord_typing_throttled",
            channel_id=getattr(channel, "id", None),
            error_type=type(e).__name__,
            status=getattr(e, "status", None),
            code=getattr(e, "code", None),
            error_msg=str(e)[:200],
        )
    except Exception as e:
        log.warning(
            "discord_typing_unexpected_error",
            channel_id=getattr(channel, "id", None),
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
        )


async def send_with_reaction_fallback(
    message: discord.Message,
    text: str,
    *,
    reaction: str = _OVERLOADED_REACTION,
) -> str:
    """Send a text reply; if the channel is rate-limited, fall back to
    a reaction on the user's original message; if that also fails,
    accept silence.

    Returns the actual delivery mode for telemetry:
      - "text"      — text reply landed
      - "reaction"  — text 429-d, reaction landed
      - "silent"    — both failed; logged, accepted (memory rule
                       ``seco_is_acceptable.md``)

    This guarantees the user gets *some* signal whenever any path is
    available. The pre-PR2 code re-raised silently, which produced the
    dead-bot UX from 2026-05-08T23:59 even when the bot was alive.
    """
    try:
        await message.channel.send(text)
        return "text"
    except discord.HTTPException as e:
        log.warning(
            "discord_send_throttled_falling_back_to_reaction",
            channel_id=getattr(message.channel, "id", None),
            error_type=type(e).__name__,
            status=getattr(e, "status", None),
            code=getattr(e, "code", None),
            error_msg=str(e)[:200],
        )

    try:
        await message.add_reaction(reaction)
        log.info(
            "discord_send_fallback_reaction_ok",
            channel_id=getattr(message.channel, "id", None),
            reaction=reaction,
        )
        return "reaction"
    except (discord.HTTPException, discord.Forbidden, discord.NotFound) as e:
        log.warning(
            "discord_send_fallback_reaction_failed",
            channel_id=getattr(message.channel, "id", None),
            reaction=reaction,
            error_type=type(e).__name__,
            error_msg=str(e)[:200],
        )

    # Both paths failed. Silence is acceptable here — the user sees
    # nothing this turn, but the next turn (after cooldown) will work.
    # The KQL alert documented in docs/runbook_alerts.md catches the
    # pattern of repeated silence so this does not go unnoticed.
    log.warning(
        "discord_send_silent_giving_up",
        channel_id=getattr(message.channel, "id", None),
    )
    return "silent"


def spawn_typing_indicator(
    channel: discord.abc.Messageable,
    spawn_task,
) -> None:
    """Convenience wrapper: schedule ``emit_typing_safe`` via the cog's
    task spawner so it's tracked for graceful shutdown without blocking
    the caller's critical path."""
    spawn_task(emit_typing_safe(channel), name="typing_indicator")


# Discord's typing indicator times out at ~10s, so we re-fire every TYPING_KEEPALIVE_S
# while the LLM is in flight. 7s gives a 3s safety margin against drift.
TYPING_KEEPALIVE_S = 7.0


async def _typing_keepalive_loop(channel: discord.abc.Messageable) -> None:
    """Re-emit ``send_typing`` every ~7s until cancelled.

    Spawned by ``spawn_typing_keepalive`` and cancelled by the caller when
    the long operation (LLM call, agent runner round-trip) finishes. Each
    iteration swallows rate-limit errors via ``emit_typing_safe`` so a
    transient 429 on the typing bucket never bubbles up and breaks the turn.
    """
    while True:
        await emit_typing_safe(channel)
        try:
            await asyncio.sleep(TYPING_KEEPALIVE_S)
        except asyncio.CancelledError:
            return


def spawn_typing_keepalive(
    channel: discord.abc.Messageable,
) -> asyncio.Task:
    """Start a background keepalive task that re-emits typing every ~7s.

    Returns the task so the caller can cancel it when their long-running
    operation completes (typically: ``finally: task.cancel()`` around the
    LLM call). Cancellation is fire-and-forget — we don't await the task
    after cancel because there's nothing to wait for: the loop exits on
    CancelledError and that's the end of it.

    Use this for operations >10s (the Discord typing TTL). For short bursts
    (<10s) the one-shot ``emit_typing_safe`` is enough and cheaper.
    """
    return asyncio.create_task(
        _typing_keepalive_loop(channel),
        name="typing_keepalive",
    )


__all__ = [
    "FailoverDecision",
    "FailoverReason",
    "FailureClass",
    "StageFailure",
    "classify_discord_exception",
    "classify_failover_reason",
    "decide_failover",
    "emit_typing_safe",
    "send_with_reaction_fallback",
    "spawn_typing_indicator",
    "spawn_typing_keepalive",
]


# --- Compatibility imports used by tests / future stages ---
# Kept here so ``test_failure.py`` can monkey-patch ``asyncio.sleep``
# without needing to know which module owns the sleep.
_ = asyncio  # silence unused-import linters in case sleep moves later
