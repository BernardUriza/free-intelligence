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

El boleto del host (2026-09-23): cada `deliver_or_fallback` acuña UN `turn_id`.
El reintento lo REUSA sólo cuando el primer intento fue `unreachable` — el
gateway se reinició o el poll dio 404, y el host no sabe qué pasó; un gateway
con ledger contesta entonces lo que de verdad ocurrió (`delivered` incluido)
en vez de correr el turno otra vez. Tras un `failed` declarado el reintento
lleva un id NUEVO: ese turno provablemente no entregó nada, y reusar el id sólo
haría eco del fallo. Un `uncertain` (el gateway murió entre "enviando" y
"entregado") no se reintenta ni se tapa con el aviso de la casa: se loggea en
rojo y se para.

Every step is a KQL event that can go red — the whole point of owning it.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from demux_ai.summon import TURN_TAKEN, TURN_UNCERTAIN, summon_and_wait
from shared.personas.registry import get_persona

log = structlog.get_logger()

RETRY_INVITED_BY = "host_retry"
REUSE_TURN_ID_AFTER = frozenset({"unreachable"})

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


def _first_turn_id(trigger_message_id: str | None, persona_id: str | None, channel_id: str) -> str:
    """Turn id for the FIRST summon of a turn.

    Deterministic from (trigger_message_id, persona_id, channel_id) so two host
    replicas overlapping in a rollover — both processing the SAME trigger for the
    SAME persona — mint the SAME id, and the gateway's durable ticket
    (`TicketRegistry.submit` → `ticket_reused`) collapses the double dispatch into
    one turn (the 2026-07-20 bug: 2 Insult replies, 2 assistant rows, vision twice).
    Including persona_id keeps a multi-persona fanout on one trigger distinct (each
    persona still answers). No trigger (proactive turns) → uuid4, nothing to dedupe
    against. The RETRY id is minted separately by the caller: a `failed` turn gets a
    fresh uuid4 so a legitimate second attempt is never deduped against the first.
    """
    if not trigger_message_id:
        return uuid.uuid4().hex
    seed = f"{trigger_message_id}:{persona_id or ''}:{channel_id}"
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


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
    turn_id = _first_turn_id(trigger_message_id, persona_id, channel_id)
    outcome = await summon(tool_input, invited_by=invited_by, turn_id=turn_id, **common)
    if outcome in TURN_TAKEN:
        log.info(
            "host_turn_delivered", channel_id=channel_id, target=persona_id, outcome=outcome, attempt=1, turn_id=turn_id
        )
        return outcome
    if outcome in TURN_UNCERTAIN:
        log.error("host_turn_uncertain", channel_id=channel_id, target=persona_id, attempt=1, turn_id=turn_id)
        return outcome
    log.warning(
        "host_turn_failed", channel_id=channel_id, target=persona_id, outcome=outcome, attempt=1, turn_id=turn_id
    )

    reused = outcome in REUSE_TURN_ID_AFTER
    retry_id = turn_id if reused else uuid.uuid4().hex
    retry = await summon(tool_input, invited_by=RETRY_INVITED_BY, turn_id=retry_id, **common)
    if retry in TURN_TAKEN:
        log.info(
            "host_turn_recovered",
            channel_id=channel_id,
            target=persona_id,
            outcome=retry,
            attempt=2,
            turn_id=retry_id,
            reused_turn_id=reused,
        )
        return retry
    if retry in TURN_UNCERTAIN:
        log.error(
            "host_turn_uncertain",
            channel_id=channel_id,
            target=persona_id,
            attempt=2,
            turn_id=retry_id,
            reused_turn_id=reused,
        )
        return retry
    log.error(
        "host_turn_gave_up",
        channel_id=channel_id,
        target=persona_id,
        outcome=retry,
        first_outcome=outcome,
        attempt=2,
        turn_id=retry_id,
        reused_turn_id=reused,
    )
    try:
        await say(channel_id, FALLBACK_TEXT.format(persona=persona_label(persona_id)))
        log.info("host_fallback_posted", channel_id=channel_id, target=persona_id)
    except Exception:
        log.exception("host_fallback_failed", channel_id=channel_id, target=persona_id)
    return retry
