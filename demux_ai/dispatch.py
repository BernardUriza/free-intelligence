"""Route a batched turn to a persona and dispatch it (#6, slice 2).

The omnipresent host, once it has a debounced batch (`demux_ai.batch`), asks the
router brain WHO should answer and hands the turn to that persona through the
gateway `/invite` (`demux_ai.summon`). This is the seam that makes Insult stop
being the structural owner of reception: the HOST receives, the router decides,
and every persona — Insult included — is just a routing target now.

Reuses what already exists (Art. 6): the router (`LLMShadowRouter` /
`DirectAzureLLMRouter`, any `.route(text) -> decision` with a `.target`) and
`summon_persona`. This module only composes them, fail-safe on every edge — a
routing fault must never wedge the host's loop.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

import structlog

from demux_ai.llm_shadow_router import DEFAULT_TARGET
from demux_ai.summon import summon_persona

log = structlog.get_logger()


class _Router(Protocol):
    async def route(self, text: str, context: str | None = None) -> Any: ...


@dataclass(frozen=True)
class RouterFaultDecision:
    """Decision shape used when the router brain itself faulted.

    A dead receptionist must not mute the house. The provider split is the whole
    resilience play — the host runs on Azure gpt-4.1 and every persona runs on
    the Claude runner — so an Azure outage (or a content-filter rejection) leaves
    the personas perfectly able to answer, and returning None here threw that
    away: the user got NO reply, NO "…", and no signal anything had failed. The
    router already defaults to Insult when the brain replies with garbage; a
    brain that raises is the same case for the turn, so it gets the same default.
    """

    target: str
    reason: str = "router_fault"


@dataclass(frozen=True)
class MentionDecision:
    """Decision shape returned when an explicit @mention bypasses the LLM router.

    `targets` holds EVERY mentioned persona — naming four personas summons four.
    `target` stays the first one so existing telemetry keeps reading a scalar.
    """

    target: str
    reason: str = "mention"
    targets: tuple[str, ...] = ()


async def route_and_dispatch(
    router: _Router,
    *,
    channel_id: str,
    text: str,
    user_name: str = "",
    guild_id: str | None = None,
    channel_name: str | None = None,
    context: str | None = None,
    trigger_message_id: str | None = None,
    forced_targets: list[str] | None = None,
    voice_transcript: str = "",
    prev_target: str | None = None,
) -> Any | None:
    """Route `text` to a persona and summon it. Returns the decision that was
    acted on (for telemetry) — never None once a message has been received.

    The persona is reached through the gateway `/invite`; the reason carries the
    user's ask verbatim (capped) so the summoned persona reads what it's answering.
    A routing exception is logged and degrades to `DEFAULT_TARGET` — the host keeps
    receiving AND the user still gets an answer.

    `voice_transcript` rides UNCAPPED and separate from the capped reason: the
    host owns susurro, so this is the persona's only copy of what was said, and
    a 600-char cap would silently truncate a long voice note.
    """
    if forced_targets:
        reason = f"{user_name}: «{text[:600]}»" if user_name else text[:600]
        # Every mentioned persona is summoned, concurrently: "@Vultur @Insult
        # @frugi @A.L.I.C.E. cuéntenme cada quien" must wake four, not the last
        # one to survive an overwrite. One failed summon never costs the others.
        outcomes = await asyncio.gather(
            *(
                summon_persona(
                    {"reason": reason},
                    channel_id=channel_id,
                    guild_id=guild_id,
                    channel_name=channel_name,
                    persona_id=persona_id,
                    invited_by="host",
                    trigger_message_id=trigger_message_id,
                    trigger_transcript=voice_transcript,
                )
                for persona_id in forced_targets
            ),
            return_exceptions=True,
        )
        for persona_id, outcome in zip(forced_targets, outcomes, strict=True):
            if isinstance(outcome, BaseException):
                log.warning(
                    "host_mention_summon_failed",
                    channel_id=channel_id,
                    target=persona_id,
                    error=f"{type(outcome).__name__}: {outcome}",
                )
                continue
            log.info(
                "host_mention_shortcircuit",
                channel_id=channel_id,
                target=persona_id,
                accepted=outcome,
                mentioned=list(forced_targets),
                # El bypass por mención NO pasa por el cerebro, así que sin este
                # campo los turnos mencionados y los ruteados se mezclan en KQL y
                # cualquier tasa de sesgo sale contaminada. `fanout` mide además
                # cuántas personas despertó una sola frase.
                prev_target=prev_target or "",
                fanout=len(forced_targets),
            )
        return MentionDecision(target=forced_targets[0], targets=tuple(forced_targets))

    try:
        decision = await router.route(text, context)
    except Exception:
        log.exception("host_dispatch_router_failed", channel_id=channel_id, fallback=DEFAULT_TARGET)
        decision = RouterFaultDecision(target=DEFAULT_TARGET)

    target = getattr(decision, "target", None)
    if not target:
        log.warning("host_dispatch_no_target", channel_id=channel_id)
        return decision

    reason = f"{user_name}: «{text[:600]}»" if user_name else text[:600]
    accepted = await summon_persona(
        {"reason": reason},
        channel_id=channel_id,
        guild_id=guild_id,
        channel_name=channel_name,
        persona_id=target,
        invited_by="host",
        trigger_message_id=trigger_message_id,
        trigger_transcript=voice_transcript,
    )
    log.info(
        "host_dispatched",
        channel_id=channel_id,
        target=target,
        accepted=accepted,
        reason=getattr(decision, "reason", ""),
        # --- instrumentación del ruteo (2026-08-06) ---
        # Sin estos campos el 97.6% de sesgo hacia insult fue INVISIBLE por tres
        # semanas: `reason` decía `llm_insult` (clean match) en cada turno, que se
        # lee como salud. Lo que faltaba era con QUÉ decidió el cerebro y contra
        # QUÉ venía. Cada campo existe para una pregunta que KQL hoy no podía
        # contestar — ver .claude/rules/router-observability.md.
        has_context=context is not None,
        context_lines=len(context.splitlines()) if context else 0,
        prev_target=prev_target or "",
        switched=bool(prev_target) and prev_target != target,
        effort=getattr(decision, "effort", ""),
    )
    return decision
