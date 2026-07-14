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

from khimeras_shared.behavior import (
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    classify_preset,
    compute_vulnerability_score,
    is_vulnerable_overlay_selection,
)

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


def build_turn_guidance(
    *,
    current_message: str,
    recent_messages: list[dict] | None,
    user_facts: list[dict] | None,
    persona_id: str,
) -> str | None:
    """Classify this turn and render the persona's guidance for it.

    Returns None when there is nothing to say (empty message, no content for this
    persona, or ANY fault). The overlay is appended whenever the selection's
    reason marks it — including the clinical-vocabulary case, where the overlay
    matters MOST (a vulnerable user asking about their own medication).
    """
    if not current_message.strip():
        return None
    try:
        selection = classify_preset(current_message, recent_messages, user_facts)
        parts = [build_preset_prompt(selection, persona_id)]
        overlay_on = is_vulnerable_overlay_selection(selection)
        if overlay_on:
            parts.append(build_vulnerable_overlay_prompt(persona_id))
        guidance = "\n\n".join(p for p in parts if p and p.strip()).strip()
        if not guidance:
            return None
        if len(guidance) > MAX_GUIDANCE_CHARS:
            log.warning(
                "guidance_truncated",
                persona_id=persona_id,
                chars=len(guidance),
                cap=MAX_GUIDANCE_CHARS,
            )
            guidance = guidance[:MAX_GUIDANCE_CHARS]
        log.info(
            "guidance_built",
            persona_id=persona_id,
            preset=selection.mode.value,
            modifiers=[m.value for m in selection.modifiers],
            reason=selection.reason[:80],
            vulnerable_overlay=overlay_on,
            vulnerability_score=compute_vulnerability_score(user_facts),
            guidance_chars=len(guidance),
        )
        return guidance
    except Exception:
        log.exception("guidance_build_failed", persona_id=persona_id)
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
    )
