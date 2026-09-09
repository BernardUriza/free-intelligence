"""Per-turn behavioral guidance — the bridge from the engine to the model.

The behavior engine (`khimeras_shared.behavior`) reads the USER's state and picks
a mode; the runner injects `behavioral_guidance` into the user message
(`persona_runner.engine.framing.frame_turn_text`), keeping the persona's system
prompt cache-stable. Between those two lived NOTHING: the engine ran only to pick
a MODEL (and without facts), so the guidance never reached the model.

The consequence that makes this a P0 rather than a feature: the vulnerable-user
overlay — clinical-source discipline, an allowlist of medical references, Mexican
crisis lines, warmth over abrasiveness — is gated on the accumulated facts of the
user. With no guidance on the wire, a user with a clinical cluster (a named
diagnosis + psychiatric medication) received the persona's raw abrasive register.
That is the exact regression `tests/core/test_presets_clinical.py` was written to
prevent, and it was live from the day the plumbing was purged (2026-07-14) until
this module.

FAIL-SAFE BY CONSTRUCTION: every failure path — no memory store, a dead DB, a
raising classifier — returns None. A turn without guidance is a normal turn; a
classification fault must NEVER cost the turn or mute the bot.
"""

from __future__ import annotations

from typing import Any

import structlog

from khimeras_shared.audit import log_crisis_band_absent, log_crisis_band_classified
from khimeras_shared.behavior import (
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    classify_preset,
    compute_vulnerability_score,
    crisis_verdict,
    is_vulnerable_overlay_selection,
)
from khimeras_shared.constraints import build_constraints_block
from khimeras_shared.gifs import catalog_block

log = structlog.get_logger()

# The runner's TurnRequest caps `behavioral_guidance` at 16000 chars and rejects
# an over-long payload with a 422 — which would turn a safety feature into a mute
# bot. We truncate HERE, loudly, so the turn always ships.
MAX_GUIDANCE_CHARS = 16000


async def load_user_facts(memory: Any, user_id: str) -> list[dict]:
    """The user's accumulated facts, or [] on any failure.

    Facts are what make the guardian work: the vulnerability score is computed
    from them (a clinical CLUSTER, not a single mention). A fact-store failure
    degrades to an unscored turn, never to a dropped turn.
    """
    if memory is None or not user_id:
        return []
    try:
        return await memory.get_facts(user_id)
    except Exception:
        log.exception("guidance_facts_load_failed", user_id=user_id)
        return []


def _registrar_veredicto(
    *,
    current_message: str,
    user_facts: list[dict] | None,
    persona_id: str,
    user_id: str,
) -> None:
    """Calcula la banda del turno y la registra. NUNCA levanta.

    Issue #53 — MODO OBSERVACIÓN: la banda se calcula y se registra; NO entra
    al guidance ni cambia lo que una persona lee.

    Issue #54 — el veredicto deja de vivir escondido dentro de `guidance_built`
    y sale con nombre propio, con su denominador y sin una palabra de quien
    escribió. El recorte de `reasons` a 3 y el seudónimo viven en
    `khimeras_shared.audit`, no aquí: son la decisión de Álex y tienen que ser
    imposibles de olvidar en el siguiente llamador.

    POR QUÉ ES UNA FUNCIÓN Y NO UN BLOQUE INLINE. La regla dura del #54 es que
    una falla del registro no puede costar el turno. Inline, dentro del try
    grande de `build_turn_guidance`, una excepción al REGISTRAR caía al
    `except` general y el turno se iba sin guidance — o sea, una persona
    vulnerable perdía su overlay porque un log se atragantó. Aquí la garantía
    es estructural: esta función se traga todo y el guidance sigue su camino.

    Los dos `reason` distinguen fallas que NO son la misma cosa:
    `crisis_band_failed` (fi-core no pudo clasificar) contra
    `crisis_band_log_failed` (hubo veredicto y lo que se cayó fue el registro).
    Un denominador que las mezcla miente justo donde existe para no mentir.
    """
    try:
        verdict = crisis_verdict(current_message, user_facts)
    except Exception:
        log.warning("crisis_band_failed", persona_id=persona_id)
        log_crisis_band_absent(persona_id=persona_id, reason="crisis_band_failed")
        return
    try:
        log_crisis_band_classified(
            band=verdict.level.value,
            gravity=verdict.score.final_gravity,
            reasons=[f"{r.kind}:{r.key}:{r.weight:+g}" for r in verdict.score.reasons],
            critical_override=verdict.score.critical_override,
            signals=list(verdict.acute.matched) if verdict.acute is not None else [],
            persona_id=persona_id,
            user_id=user_id,
        )
    except Exception:
        log.exception("crisis_band_log_failed", persona_id=persona_id)
        log_crisis_band_absent(persona_id=persona_id, reason="crisis_band_log_failed")


def build_turn_guidance(
    *,
    current_message: str,
    recent_messages: list[dict] | None,
    user_facts: list[dict] | None,
    persona_id: str,
    user_id: str = "",
) -> str | None:
    """Classify this turn and render the persona's guidance for it.

    Returns None when there is nothing to say (empty message, no content for this
    persona, or ANY fault). The overlay is appended whenever the selection's
    reason marks it — including the clinical-vocabulary case, where the overlay
    matters MOST (a vulnerable user asking about their own medication).
    """
    if not current_message.strip():
        log_crisis_band_absent(persona_id=persona_id, reason="mensaje_vacio")
        return None
    # Issue #54: el par classified/absent se emite UNA vez por turno. Sin esta
    # bandera, una falla posterior al veredicto lo contaría en los dos lados y
    # el denominador mentiría justo donde existe para no mentir.
    registrado = False
    try:
        selection = classify_preset(current_message, recent_messages, user_facts)
        # Invariants go FIRST: the 16k truncation below must eat preset prose
        # before it ever eats a hard restriction (2026-07-23 — see
        # `khimeras_shared.constraints`).
        constraints = build_constraints_block(user_facts)
        parts = [constraints] if constraints else []
        parts.append(build_preset_prompt(selection, persona_id))
        overlay_on = is_vulnerable_overlay_selection(selection)
        if overlay_on:
            parts.append(build_vulnerable_overlay_prompt(persona_id))
        # A persona cannot use a repertoire it was never shown: without the tag
        # list the model either never emits [GIF:] or invents a tag that resolves
        # to nothing. Absent catalog → block is None → feature simply off.
        gif_block = catalog_block(persona_id)
        if gif_block:
            parts.append(gif_block)
        guidance = "\n\n".join(p for p in parts if p and p.strip()).strip()
        if not guidance:
            log_crisis_band_absent(persona_id=persona_id, reason="sin_guidance")
            registrado = True
            return None
        if len(guidance) > MAX_GUIDANCE_CHARS:
            log.warning(
                "guidance_truncated",
                persona_id=persona_id,
                chars=len(guidance),
                cap=MAX_GUIDANCE_CHARS,
            )
            guidance = guidance[:MAX_GUIDANCE_CHARS]
        _registrar_veredicto(
            current_message=current_message,
            user_facts=user_facts,
            persona_id=persona_id,
            user_id=user_id,
        )
        registrado = True
        log.info(
            "guidance_built",
            persona_id=persona_id,
            preset=selection.mode.value,
            modifiers=[m.value for m in selection.modifiers],
            reason=selection.reason[:80],
            constraints=constraints.count("\n- ") if constraints else 0,
            vulnerable_overlay=overlay_on,
            vulnerability_score=compute_vulnerability_score(user_facts),
            guidance_chars=len(guidance),
        )
        return guidance
    except Exception:
        log.exception("guidance_build_failed", persona_id=persona_id)
        if not registrado:
            log_crisis_band_absent(persona_id=persona_id, reason="guidance_build_failed")
        return None


async def guidance_for_turn(
    *,
    memory: Any,
    user_id: str,
    current_message: str,
    recent_messages: list[dict] | None,
    persona_id: str,
) -> str | None:
    """Load facts + classify + render, in one fail-safe call for the turn path."""
    facts = await load_user_facts(memory, user_id)
    return build_turn_guidance(
        current_message=current_message,
        recent_messages=recent_messages,
        user_facts=facts,
        persona_id=persona_id,
        user_id=user_id,
    )
