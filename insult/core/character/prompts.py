"""Layered system-prompt assembly.

`build_adaptive_prompt` composes the system prompt one layer at a time and
returns it together with the `PresetSelection` the classifier picked, so the
caller can log which preset drove the turn. Each layer is conditional:

- 0-2: persona (immutable, cached) — the caller passes `base_prompt`.
- 3:   preset behavioral guidance.
- 3.1: vulnerable-user safety overlay (only when the preset selection flags it).
- 3.5: 4-flow guidance (epistemic / pressure / expression / awareness).
- 3.7: server pulse — cross-channel awareness blurb.
- 4:   per-user style adaptation (only when the profile is confident).
- Reactive guards: anti-sycophancy + correction-protocol.
- Length hint when recent responses are too uniform.
- Identity reinforcement once the conversation crosses
  ``IDENTITY_REINFORCE_THRESHOLD``.

Beyond layer 3 the prompt becomes per-request, so a ``CACHE_BOUNDARY`` marker
goes in right after ``base_prompt``; ``llm._send`` splits on it to mark the
prefix as cacheable.
"""

from __future__ import annotations

import re

import structlog

from insult.core.character.detection import (
    CACHE_BOUNDARY,
    IDENTITY_REINFORCE_THRESHOLD,
    IDENTITY_REINFORCEMENT_SUFFIX,
)
from insult.core.character.time_context import _get_current_time_context
from insult.core.flows import FlowAnalysis, build_flow_prompt
from insult.core.presets import (
    PresetSelection,
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
    classify_preset,
    is_vulnerable_overlay_selection,
)

log = structlog.get_logger()


def build_adaptive_prompt(
    base_prompt: str,
    profile,
    context_len: int,
    *,
    current_message: str = "",
    recent_messages: list[dict] | None = None,
    user_facts: list[dict] | None = None,
    flow_analysis: FlowAnalysis | None = None,
    server_pulse: str = "",
    recent_response_lengths: list[int] | None = None,
) -> tuple[str, PresetSelection]:
    """Compose the system prompt and return (prompt, preset_selection)."""
    # base_prompt (persona.md) is the only 100% stable section — mark the cache
    # boundary right after it so the Anthropic cache covers ~10K tokens of persona
    # across requests. Everything appended below is dynamic.
    prompt = base_prompt + CACHE_BOUNDARY

    # --- Time awareness (always inject) ---
    time_ctx = _get_current_time_context()
    prompt += (
        f"\n\n## Current Time\nRight now it is: {time_ctx}. Use this naturally — don't announce it unless relevant."
        "\n\nIMPORTANT: The conversation messages include metadata like [hace 2h] timestamps and "
        "speaker labels (e.g. 'bernard2389:'). These are for YOUR context only. "
        "NEVER reproduce timestamps, speaker labels, or '[SEND]' markers in your responses. "
        "Just respond as pure text — no prefixes, no metadata, no formatting artifacts."
    )

    # --- Layer 3: Preset behavioral guidance ---
    preset = classify_preset(current_message, recent_messages, user_facts)
    preset_prompt = build_preset_prompt(preset)
    prompt += f"\n\n{preset_prompt}"

    # --- Layer 3.1: Vulnerable-user safety overlay ---
    # Appended only when the classifier routed here via the vulnerable-user
    # branch (accumulated clinical/trauma signals in the user's facts). This
    # overlay overrides the abrasive persona for this turn; see
    # insult/core/presets.py::_VULNERABLE_OVERLAY_PROMPT for the exact rules
    # and insult/core/vulnerability.py for the scoring that flags a user.
    if is_vulnerable_overlay_selection(preset):
        prompt += build_vulnerable_overlay_prompt()

    log.info(
        "preset_classified",
        mode=preset.mode.value,
        modifiers=[m.value for m in preset.modifiers],
        confidence=round(preset.confidence, 2),
        reason=preset.reason,
        vulnerable_overlay=is_vulnerable_overlay_selection(preset),
    )

    # --- Layer 3.5: Flow behavioral guidance ---
    if flow_analysis:
        flow_prompt = build_flow_prompt(flow_analysis)
        if flow_prompt:
            prompt += f"\n\n{flow_prompt}"

    # --- Layer 3.7: Server Pulse (cross-channel awareness) ---
    if server_pulse:
        prompt += f"\n\n{server_pulse}"

    # --- Layer 4: Style adaptation (per-user) ---
    if profile and profile.is_confident:
        adaptations = []

        if profile.detected_language == "en":
            adaptations.append("This user writes in English. Respond in English but keep your personality.")

        if profile.avg_word_count < 10:
            adaptations.append(
                "This user tends to be brief. You can match their energy OR surprise them with depth — "
                "your call as Insult. Don't lock yourself into always being short."
            )
        elif profile.avg_word_count > 40:
            adaptations.append(
                "This user writes long messages. You might go deep with them, or you might dismiss a wall of "
                "text with a single emoji. Let the content decide, not the length."
            )

        if profile.formality < 0.25:
            adaptations.append(
                "This user is very casual and uses slang freely. You can go full vulgar — they can take it."
            )
        elif profile.formality > 0.6:
            adaptations.append(
                "This user is more formal. Dial back the vulgar words but keep the confrontational edge. "
                "Be sharp with vocabulary, not crude."
            )

        if profile.technical_level > 0.6:
            adaptations.append(
                "This user is technical. Use precise terminology, reference specific patterns, "
                "and critique at architecture level. Skip basic explanations."
            )
        elif profile.technical_level < 0.2:
            adaptations.append(
                "This user is not very technical. Use analogies and simple language when explaining. "
                "Still challenge them, but make your points accessible."
            )

        if profile.emoji_ratio > 0.05:
            adaptations.append("This user uses emojis. You can use them sparingly for emphasis.")

        if adaptations:
            prompt += "\n\n## User Adaptation (adjust your style, NOT your identity)\n"
            prompt += "\n".join(f"- {a}" for a in adaptations)

    # --- Fix #2: Anti-sycophancy — detect sustained agreement (reactive) ---
    if recent_messages and len(recent_messages) >= 4:
        # Check last 2 assistant messages for agreement patterns
        assistant_msgs = [m for m in recent_messages if m["role"] == "assistant"][-2:]
        agreement_words = re.compile(r"(?i)\b(exacto|exactamente|tienes raz[oó]n|correcto|s[ií] carnal|bien dicho)\b")
        agreements = sum(1 for m in assistant_msgs if agreement_words.search(m.get("content", "")))
        if agreements >= 2:
            prompt += (
                "\n\n## Anti-Sycophancy Alert\n"
                "You have AGREED with the user's last 2 messages. Your NEXT response MUST contain "
                "a counter-argument, a hole in their logic, or a question that forces them to defend "
                "their position. Sustained agreement is character death for Insult."
            )

    # --- Preventive correction protocol (runs BEFORE the LLM, not after) ---
    # Reactive guard above only fires AFTER two capitulations. This one looks
    # at the current user message for pushback aimed *at the bot* and injects
    # a how-to-handle-it block. Patterns MUST be narrow — a false positive
    # forces "concede in one line" and shrinks unrelated responses.
    correction_signal = re.compile(
        r"(?i)("
        # Spanish: pronoun-targeted ("estás mal TU", "TU no sabes", "TE equivocaste")
        r"\best[aá]s?\s+mal\b|"
        r"\bte\s+equivocaste\b|"
        r"\bte\s+(pasaste|confundes|falla)\b|"
        r"\bno\s+te\s+(creo|conf[ií]o)\b|"
        r"\bpor\s+eso\s+no\s+conf[ií]o\b|"
        # Spanish: explicit falsehood claims about the bot's statement
        r"\beso\s+(que\s+dices\s+)?no\s+es\s+(cierto|verdad|as[ií])\b|"
        r"\bestas\s+equivocad[oa]\b|"
        # English: explicit wrong/disagree aimed at bot
        r"\byou'?re\s+wrong\b|"
        r"\byou\s+got\s+it\s+wrong\b|"
        r"\bthat'?s\s+(not\s+true|wrong|incorrect)\b"
        r")"
    )
    correction_fired = bool(current_message and correction_signal.search(current_message))
    if correction_fired:
        prompt += (
            "\n\n## Correction Protocol (user is pushing back)\n"
            "The user is contradicting you. Your response MUST do ONE of:\n"
            "(a) Defend with specifics — cite data, quote the claim, show the reasoning.\n"
            "(b) Turn it back — 'a ver, muéstrame por qué', force them to bring evidence.\n"
            "(c) Concede in ONE grudging line and pivot — 'Ok, fair, me equivoqué. Pero...'.\n"
            "FORBIDDEN: apologizing, self-mocking, 'cierra la boca Insult', 'no sé leer mapas', "
            "disclaimers of your own competence. Folding without dignity is character death — "
            "being wrong is recoverable, being servile is not."
        )

    # --- Fix #3: Length variation hint ---
    # Suppressed when Correction Protocol is active — the protocol already
    # dictates response shape (defend / redirect / concede-one-line) and
    # stacking a separate length hint on top produced over-compression.
    if recent_response_lengths and not correction_fired:
        from insult.core.character.formatting import get_length_hint

        hint = get_length_hint(recent_response_lengths)
        if hint:
            prompt += f"\n\n{hint}"

    # --- Identity reinforcement for long conversations ---
    if context_len >= IDENTITY_REINFORCE_THRESHOLD:
        prompt += IDENTITY_REINFORCEMENT_SUFFIX

    return prompt, preset


# ---------------------------------------------------------------------------
# Post-build composition helpers
# ---------------------------------------------------------------------------
#
# `build_adaptive_prompt` runs before the caller has computed flow_analysis,
# arc_state, stances, etc. (some of those depend on the preset that this
# function returns). Once those are ready, the caller stitches them onto
# the prompt in turn.py. `compose_extra_layers` keeps that stitching
# declarative — one named-arg per layer, empty blocks skipped — instead of
# a chain of `if X: prompt += "\n\n" + X`.


def _format_other_people_block(facts: dict[str, list[dict]]) -> str:
    """Render the "Other People in This Channel" block (top 3 facts each)."""
    parts = ["## Other People in This Channel (they are REAL — never say they don't exist)"]
    for name, person_facts in facts.items():
        fact_lines = ", ".join(f["fact"] for f in person_facts[:3])
        parts.append(f"- {name}: {fact_lines}")
    return "\n".join(parts)


def compose_extra_layers(
    base_prompt: str,
    *,
    flow_prompt: str = "",
    arc_prompt: str = "",
    stance_prompt: str = "",
    facts_prompt: str = "",
    other_participants_facts: dict[str, list[dict]] | None = None,
) -> str:
    """Append optional layers to a base system prompt, skipping empty blocks.

    Each non-empty block is joined with ``\\n\\n``. ``facts_prompt`` may
    arrive with its own leading newline pair (legacy quirk of
    ``build_facts_prompt``); we ``lstrip`` to normalize so concatenation
    never produces runs of three or more blank lines.
    """
    out = base_prompt
    for block in (flow_prompt, arc_prompt, stance_prompt, facts_prompt):
        if block:
            out += "\n\n" + block.lstrip()
    if other_participants_facts:
        out += "\n\n" + _format_other_people_block(other_participants_facts)
    return out
