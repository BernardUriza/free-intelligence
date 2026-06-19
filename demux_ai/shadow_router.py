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


# The persona_id the persona pipeline uses for the default target. ``shadow_route``
# speaks in concrete persona names ("insult"); the pipeline encodes the default
# persona as ``None`` (TurnCtx.persona_id is None → Insult downstream). This maps
# the router vocabulary onto the pipeline's, so the cutover sets exactly what the
# live @vultur rule would have set.
_DEFAULT_PERSONA_ID: str | None = None


def apply_cutover(*, live_persona_id: str | None, decision: ShadowDecision) -> str | None:
    """HOST 5/6 slice B — translate a deterministic shadow decision into the
    persona_id the turn should ACTUALLY run as under cutover.

    Pure, no I/O, no LLM — this is the host's routing decision expressed in the
    pipeline's ``persona_id`` vocabulary (``None`` == the default/Insult persona).
    ``live_persona_id`` is what the live ``@vultur`` rule already set; it is passed
    in so the caller can log live-vs-cutover divergence, but the returned value is
    derived purely from ``decision`` (the cutover is what now OWNS routing).

    Slice-B invariant: because the deterministic ``shadow_route`` mirrors the live
    rule by construction, the returned value equals ``live_persona_id`` for every
    input today — so acting on it is a true no-op. The seam still genuinely routes
    (a future, divergent router would return a different persona here), which is
    the structural cutover slice B exists to prove.
    """
    if decision.target == _DEFAULT_TARGET:
        return _DEFAULT_PERSONA_ID
    return decision.target


__all__ = ["ShadowDecision", "apply_cutover", "shadow_route"]
