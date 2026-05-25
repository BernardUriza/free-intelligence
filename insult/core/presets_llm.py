"""LLM-based preset classifier — `decisional middleware` for preset selection.

**DEPRECATED (v3.9.25, 2026-05-14)** — replaced by the persona's
"Implicit Mode Reflex" clause which makes preset selection a silent
in-band behavior of the agent runner itself. The regex classifier
in `insult.core.presets.classify_preset()` still runs as a structural
signal (telemetry) but the LLM middleware here has no consumer when
the agent path is canonical. With
``PRESET_CLASSIFIER_LLM_ENABLED=false`` (or
``LEGACY_LLM_ENABLED=false``) the call returns empty and we fall
through to the regex result. Safe to delete once we confirm the
agent's mode reflex produces preset-equivalent behavior across the
full message distribution.

The regex classifier in `insult.core.presets.classify_preset()` is fast and
deterministic but blind to context. A user writing `tu sabes varios ya...`
(an explicit invitation to demonstrate memory) has zero content-word
overlap with their facts, so MEMORY_RECALL never activates and the bot
deflects instead of citing. This module replaces that decision with a
Haiku call that reads the recent thread plus the user's facts and decides
preset + modifiers from intent, not patterns.

Architecture (see `.claude/plans/preset_middleware.md` if it exists):

- `classify_preset_llm()` is the happy path: one Haiku call via
  the runner's one-shot /v1/judge via ``judge.utility_call``.
- Output is strict JSON: ``{preset, modifiers[], confidence, reason}``.
- On JSON parse failure, enum-validation failure, timeout, or API error,
  returns ``None`` — the caller falls back to the regex classifier.
- The regex classifier still runs in the same turn for telemetry
  (`preset_llm_regex_divergence` event when they disagree). F5 industry
  recommendation: combine ML + LLM rather than choose one.

Cost model: ~600 tokens cached prompt + ~80 output = ~$0.0005 per turn at
Haiku rates ($1/M input + $5/M output). At 200 turns/day this is ~$3/month,
well under the $20/week target documented in `project_model_router_planned`.

Latency: Haiku with prompt-cache typical 300-500ms. The caller is expected
to await this in parallel with other I/O (facts load, disclosure scan) so
the latency is masked. If the classifier is the critical path, the user
notices ~+400ms per turn — acceptable but not free.
"""

from __future__ import annotations

import json
import re

import structlog

from insult.core.presets import (
    PresetMode,
    PresetModifier,
    PresetSelection,
    has_channel_noun,
)
from insult.core.prompts_loader import load_prompt

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prompt — cacheable prefix + dynamic turn data
# ---------------------------------------------------------------------------
#
# Structure: 600-token preamble (cacheable across turns via the
# CACHE_BOUNDARY split in `_build_system_blocks`) + ~200 tokens of dynamic
# context per turn. Output: strict JSON, no preamble, no explanation.

_VALID_PRESETS = {
    "default_abrasive",
    "playful_roast",
    "intellectual_pressure",
    "relational_probe",
    "respectful_serious",
    "meta_deflection",
    "arc",
}

_VALID_MODIFIERS = {
    "memory_recall",
    "contempt",
    "action_intent",
    "multi_domain_synthesis",
}

# The classifier system prompt lives in `insult/prompts/preset_classifier.md`.
# Loaded via `load_prompt("preset_classifier")` INSIDE classify_preset_llm()
# (not at module level) so that mtime-based hot-reload picks up edits to the
# .md file without redeploy. See `.claude/rules/architecture.md` § Prompts.


def _build_user_turn_block(
    current_message: str,
    recent_messages: list[dict] | None,
    user_facts: list[dict] | None,
) -> str:
    """Compose the dynamic per-turn block fed to the classifier."""
    parts = []

    if user_facts:
        # Slim facts list — top 10, fact text only, no metadata.
        slim = [f.get("fact", "") for f in user_facts[:10] if f.get("fact")]
        if slim:
            facts_block = "\n".join(f"- {fact}" for fact in slim)
            parts.append(f"## User facts (long-term memory)\n{facts_block}")

    if recent_messages:
        # Last 5 messages — role + content only.
        last_5 = recent_messages[-5:]
        recent_block = "\n".join(f"[{m.get('role', '?')}] {m.get('content', '')[:200]}" for m in last_5)
        parts.append(f"## Recent thread\n{recent_block}")

    parts.append(f"## Current message\n{current_message}")
    parts.append("Classify. Output strict JSON only.")

    return "\n\n".join(parts)


# Strict JSON pattern: a single top-level object, no fences. We accept text
# that contains exactly one JSON object (even if there's whitespace or stray
# fence markers around it) and parse the first balanced {...} block.
_JSON_OBJECT_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """Pull the first JSON object out of the response text. Tolerates
    markdown fences, leading whitespace, and trailing prose."""
    if not text:
        return None
    # Fast path: the whole response is JSON.
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    # Slow path: find the first balanced object.
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _parse_classifier_response(text: str) -> PresetSelection | None:
    """Parse the Haiku response into a PresetSelection, or None if invalid.

    Validation rules (all must pass — partial bails to None so caller falls
    back to regex):
    - JSON parses
    - "preset" is one of _VALID_PRESETS
    - "modifiers" is a list of valid modifier strings (empty list OK)
    - "confidence" is a numeric in [0, 1] (clamped if out of range)
    - "reason" is a string (truncated to 200 chars)
    """
    data = _extract_json(text)
    if not isinstance(data, dict):
        return None

    preset_value = data.get("preset")
    if not isinstance(preset_value, str) or preset_value not in _VALID_PRESETS:
        return None

    modifiers_raw = data.get("modifiers", [])
    if not isinstance(modifiers_raw, list):
        return None
    modifiers: list[PresetModifier] = []
    for m in modifiers_raw:
        if isinstance(m, str) and m in _VALID_MODIFIERS:
            modifiers.append(PresetModifier(m))
        # Unknown modifier strings are silently skipped — the LLM
        # occasionally hallucinates plausible-but-undefined modifiers
        # and we'd rather drop them than reject the whole classification.

    confidence_raw = data.get("confidence", 0.7)
    try:
        confidence = max(0.0, min(1.0, float(confidence_raw)))
    except (TypeError, ValueError):
        confidence = 0.7

    reason = data.get("reason", "")
    if not isinstance(reason, str):
        reason = ""
    reason = f"llm:{reason[:200]}"

    return PresetSelection(
        mode=PresetMode(preset_value),
        modifiers=modifiers,
        confidence=confidence,
        reason=reason,
    )


async def classify_preset_llm(
    current_message: str,
    recent_messages: list[dict] | None,
    user_facts: list[dict] | None,
    judge,
    *,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 200,
) -> PresetSelection | None:
    """Call Haiku to classify preset + modifiers from context.

    Returns ``None`` on any failure (timeout, API error, invalid JSON,
    invalid preset enum). The caller MUST handle ``None`` by falling
    back to the regex classifier — this function never raises for
    routing-level failures, only for programming errors.

    Args:
        current_message: the user's current message text.
        recent_messages: last 5 turns (role/content dicts).
        user_facts: slim list of stored facts about the user.
        judge: RunnerJudgeClient — uses utility_call against /v1/judge
            (one-shot, text-only; no character-break / language cure).
        model: Haiku model id. Override per turn if needed.
        max_tokens: cap on output. 200 is plenty for the JSON shape.
    """
    user_block = _build_user_turn_block(current_message, recent_messages, user_facts)
    messages: list[dict] = [{"role": "user", "content": user_block}]

    try:
        response = await judge.utility_call(
            system_prompt=load_prompt("preset_classifier"),
            messages=messages,  # type: ignore[arg-type]
            model=model,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        # utility_call already logs llm_failed internally — we add a
        # classifier-specific event so the fallback rate is queryable.
        log.warning(
            "preset_llm_api_error",
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return None

    selection = _parse_classifier_response(response.text)
    if selection is None:
        log.warning(
            "preset_llm_invalid_response",
            text_preview=response.text[:200],
            stop_reason=response.stop_reason,
        )
        return None

    # Syntactic gate: drop ACTION_INTENT if the message has no channel noun.
    # The LLM occasionally emits action_intent for "setup/automation" messages
    # that have nothing to do with Discord channel ops — and the resulting
    # tool_choice="any" forces the model into get_channel_info as a no-op,
    # which the bot then dumps to the user as its entire response.
    # Production regression 2026-05-13: "Asi hasta tu podrias acceder a esa
    # VM..." → action_intent → Opus called get_channel_info → bot replied
    # "#general — (sin descripción)".
    if PresetModifier.ACTION_INTENT in selection.modifiers and not has_channel_noun(current_message):
        selection = PresetSelection(
            mode=selection.mode,
            modifiers=[m for m in selection.modifiers if m != PresetModifier.ACTION_INTENT],
            confidence=selection.confidence,
            reason=selection.reason + " [action_intent_gated:no_channel_noun]",
        )
        log.warning(
            "preset_llm_action_intent_gated",
            reason="no_channel_noun_in_message",
            text_preview=current_message[:120],
        )

    log.info(
        "preset_llm_classified",
        preset=selection.mode.value,
        modifiers=[m.value for m in selection.modifiers],
        confidence=round(selection.confidence, 2),
        reason=selection.reason,
        stop_reason=response.stop_reason,
    )
    return selection
