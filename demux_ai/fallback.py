"""The host owns the failure of the turns it routes (2026-09-03).

Until today a persona that could not answer a host-routed turn mumbled "…" in
its own name, from the gateway's guard, and the host — the component that
CHOSE that persona — never learned anything had failed: `/invite` answered
202 the instant the turn was scheduled. Eight times in two days Alex got an
ellipsis from Insult for a budget cut on a server she cannot see.

Now the host summons with ``wait`` (`demux_ai.summon.summon_and_wait`), reads
the real outcome, and acts on it here: one retry of the same persona (the
failures that hit prod are transient — a budget cut, a runner restarting under
a deploy, a cold gateway), and if that also fails, a notice in the HOST's voice
naming who could not answer. A retry is safe because a "failed" turn delivered
nothing: the gateway reports "delivered" the moment the user saw text, and a
fault after that is logged, never raised (`persona_gateway/turns.py`).

Every step is a KQL event that can go red — the whole point of owning it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from demux_ai.summon import TURN_TAKEN, summon_and_wait
from shared.personas.registry import get_persona

log = structlog.get_logger()

RETRY_INVITED_BY = "host_retry"

# Neutral, in the house's voice, no internals. Names the persona so the user
# knows WHO went quiet — an ellipsis under Insult's name told Alex nothing.
FALLBACK_TEXT = (
    "{persona} no alcanzó a contestar esta vez, ni al segundo intento. Repítelo en un momento y lo vuelvo a llamar."
)

Summon = Callable[..., Awaitable[str]]
Say = Callable[[str, str], Awaitable[None]]


def persona_label(persona_id: str | None) -> str:
    persona = get_persona(persona_id) if persona_id else None
    return persona.display_name if persona and persona.display_name else (persona_id or "La persona")


async def deliver_or_fallback(
    tool_input: dict,
    *,
    say: Say,
    channel_id: str,
    guild_id: str | None = None,
    channel_name: str | None = None,
    persona_id: str | None = None,
    invited_by: str | None = None,
    trigger_message_id: str | None = None,
    trigger_transcript: str = "",
    summon: Summon = summon_and_wait,
) -> str:
    """Summon, wait, retry once, then speak for the house. Returns the final
    outcome (a `TURN_TAKEN` member, or the failure that survived the retry).

    ``say(channel_id, text)`` is the host's raw sidecar send. Never raises: a
    fallback that cannot be posted is logged, and the loop that called this in
    the background keeps ticking.
    """
    common: dict[str, Any] = {
        "channel_id": channel_id,
        "guild_id": guild_id,
        "channel_name": channel_name,
        "persona_id": persona_id,
        "trigger_message_id": trigger_message_id,
        "trigger_transcript": trigger_transcript,
    }
    outcome = await summon(tool_input, invited_by=invited_by, **common)
    if outcome in TURN_TAKEN:
        log.info("host_turn_delivered", channel_id=channel_id, target=persona_id, outcome=outcome, attempt=1)
        return outcome
    log.warning("host_turn_failed", channel_id=channel_id, target=persona_id, outcome=outcome, attempt=1)

    retry = await summon(tool_input, invited_by=RETRY_INVITED_BY, **common)
    if retry in TURN_TAKEN:
        log.info("host_turn_recovered", channel_id=channel_id, target=persona_id, outcome=retry, attempt=2)
        return retry
    log.error(
        "host_turn_gave_up",
        channel_id=channel_id,
        target=persona_id,
        outcome=retry,
        first_outcome=outcome,
        attempt=2,
    )
    try:
        await say(channel_id, FALLBACK_TEXT.format(persona=persona_label(persona_id)))
        log.info("host_fallback_posted", channel_id=channel_id, target=persona_id)
    except Exception:
        log.exception("host_fallback_failed", channel_id=channel_id, target=persona_id)
    return retry
