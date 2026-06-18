"""Shadow router — the demux host's DETERMINISTIC routing decision (HOST 5/6 slice A).

The north-star ADR makes the demux host a dumb receptionist: classify intent,
pick the target persona, never serve AS a persona. Slice A is the first,
SAFEST cut of that brain: a pure, deterministic routing decision that runs in
SHADOW — the persona pipeline logs what the host WOULD route to alongside where
the turn actually goes (``current_target`` vs ``shadow_target``), so divergences
are measurable in prod BEFORE any cutover.

Deliberately NOT the gpt-4.1 ``HostRouterLLM`` (slice 1): this is config-only,
no LLM, no Azure call, no spend. The LLM intent classifier is a later, separately
gated slice — slice A only needs to mirror the live deterministic routing rule
(the ``@vultur``/``~vultur`` prefix in ``_stage_bind_identity``) so a logged
divergence means a REAL gap, not a stale shadow.

Boundary: ``demux_ai`` must never import ``personas.*`` (host→persona ratchet is
0). This module imports only stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass

# The default target when no explicit persona routing token is present. Mirrors
# ``TurnCtx.persona_id is None`` → Insult downstream.
_DEFAULT_TARGET = "insult"

# Leading routing tokens that hand a turn to a sibling persona. Kept in lockstep
# with ``personas.insult.cogs.chat.stages._VULTUR_PREFIXES`` (the live rule); the
# shadow is only meaningful while it mirrors production routing.
_VULTUR_PREFIXES = ("@vultur ", "~vultur ")


@dataclass(frozen=True)
class ShadowDecision:
    """A deterministic shadow routing decision: which persona the host would pick
    for this turn, plus the rule that fired. ``reason`` is a stable, greppable
    token (``vultur_prefix`` / ``default_insult``) so divergence telemetry can be
    aggregated by cause."""

    target: str
    reason: str


def shadow_route(text: str) -> ShadowDecision:
    """Decide the shadow routing target for ``text`` — pure, no I/O, no LLM.

    Rules (deterministic, mirror the live stage):
    - a leading ``@vultur ``/``~vultur `` token → the Vultur sibling persona.
    - anything else → the default persona (Insult).
    """
    lowered = text.lstrip().lower()
    for prefix in _VULTUR_PREFIXES:
        if lowered.startswith(prefix):
            return ShadowDecision(target="vultur", reason="vultur_prefix")
    return ShadowDecision(target=_DEFAULT_TARGET, reason="default_insult")


__all__ = ["ShadowDecision", "shadow_route"]
