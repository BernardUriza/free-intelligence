"""Rule-based preset classifier — zero-cost, fast, deterministic.

Reads the trigger tables from ``presets.patterns`` and the vulnerability
signals from ``core.vulnerability`` to pick a ``PresetSelection`` for the
current turn. Priority-ordered (safety first); see ``classify_preset``.
"""

from __future__ import annotations

import re

from khimeras_shared.behavior.patterns import count_pattern_hits as _count_pattern_hits
from khimeras_shared.behavior.presets.patterns import (
    _ARC_PATTERNS,
    _CONTEMPT_PATTERNS,
    _INTELLECTUAL_PATTERNS,
    _META_PATTERNS,
    _PLAYFUL_PATTERNS,
    _RECALL_STOPWORDS,
    _RELATIONAL_PATTERNS,
    _SERIOUS_PATTERNS,
)
from khimeras_shared.behavior.presets.types import PresetMode, PresetModifier, PresetSelection
from khimeras_shared.behavior.synthesis import detect_synthesis
from khimeras_shared.behavior.vulnerability import (
    VULNERABLE_THRESHOLD,
    compute_vulnerability_score,
    is_acute_crisis,
    matched_signal_groups,
)


def _analyze_window(messages: list[dict], patterns: list[re.Pattern]) -> int:
    """Count pattern hits across the last N messages (user messages only)."""
    total = 0
    for msg in messages:
        if msg.get("role") == "user":
            total += _count_pattern_hits(msg.get("content", ""), patterns)
    return total


def classify_preset(
    current_message: str,
    recent_messages: list[dict] | None = None,
    user_facts: list[dict] | None = None,
) -> PresetSelection:
    """Classify the current conversation into a behavioral preset.

    Uses the current message as primary signal + recent context as secondary.
    Returns PresetSelection with mode, modifiers, confidence, and debug reason.

    Priority order (highest to lowest):
    1. RESPECTFUL_SERIOUS — safety first, always wins
    2. META_DEFLECTION — identity protection
    3. ARC — ethical/systemic/deep relational territory
    4. RELATIONAL_PROBE — emotional signals
    5. INTELLECTUAL_PRESSURE — technical/argumentative signals
    6. PLAYFUL_ROAST — humor/banter signals
    7. DEFAULT_ABRASIVE — fallback
    """
    window = (recent_messages or [])[-5:]  # last 5 messages for context
    modifiers: list[PresetModifier] = []

    # --- Check modifiers first (independent of mode) ---

    # CONTEMPT: ultra-short, low-effort message
    stripped = current_message.strip()
    if stripped and len(stripped) <= 3 and _count_pattern_hits(stripped, _CONTEMPT_PATTERNS) > 0:
        modifiers.append(PresetModifier.CONTEMPT)

    # MEMORY_RECALL: check if user facts exist and could connect to current message
    if user_facts:
        msg_words = set(current_message.lower().split()) - _RECALL_STOPWORDS
        for fact in user_facts:
            fact_words = set(fact.get("fact", "").lower().split()) - _RECALL_STOPWORDS
            if len(fact_words & msg_words) >= 2:
                modifiers.append(PresetModifier.MEMORY_RECALL)
                break

    # MULTI_DOMAIN_SYNTHESIS (Phase 2.5): user is making a cross-domain conceptual
    # connection that the model probably wasn't trained to compare directly.
    # Trigger forces the LLM to research before challenging — see
    # synthesis.py and the modifier guidance for behavior contract.
    synthesis = detect_synthesis(current_message)
    if synthesis.activated:
        modifiers.append(PresetModifier.MULTI_DOMAIN_SYNTHESIS)

    # --- Priority 0: ACUTE CRISIS in current message — always wins ---
    # Explicit distress / ideation / "no puedo más" / panic NOW. Beats
    # everything else, including absence of chronic facts. A new user
    # with no fact store writing "ya no puedo más" gets the safety mode.
    if is_acute_crisis(current_message):
        return PresetSelection(
            mode=PresetMode.RESPECTFUL_SERIOUS,
            modifiers=modifiers,
            confidence=0.95,
            reason="acute_crisis_in_current_message",
        )

    # --- Priority 0.5: Chronic vulnerable overlay (F1 — split from acute) ---
    # The user crossed VULNERABLE_THRESHOLD in their long-term facts but
    # the current message is NOT an acute crisis. Before F1 we forced
    # RESPECTFUL_SERIOUS here, which produced flat "presence, not
    # performance" replies for users in stable chronic care just trying
    # to talk about their day (the DIF turn that aplanó a Alex).
    #
    # F1 routes this case to RELATIONAL_PROBE — a movement-permitting
    # preset whose guidance ("Be direct, not soft", "Ask the question
    # they're avoiding", "AVOID therapy-speak, platitudes, fake empathy",
    # "challenge them, but the challenge serves THEM") naturally aligns
    # with the chronic-care directive "sharpness capped, movement
    # preserved". ARC was considered and rejected — its guidance carries
    # too much old machinery (mechanism-naming, system-critique sub-
    # sections, ideology rhetoric) that bloats the prompt for a user
    # who just wants to talk about their day under the overlay.
    #
    # The new reason `chronic_nonacute_move_allowed` is recognised by
    # is_vulnerable_overlay_selection (see _OVERLAY_REASON_PREFIXES),
    # so the safety overlay still activates downstream — but the prefix
    # makes the routing explicit in telemetry instead of hiding under
    # the legacy `vulnerable_user_overlay` umbrella.
    #
    # Exception: if the current message itself matches _SERIOUS_PATTERNS
    # (clinical vocabulary like "quetiapina", "trauma", "psiquiatra"),
    # we let Priority 1 handle it as RESPECTFUL_SERIOUS — the current-
    # message signal is stronger than the chronic prior in those turns.
    vuln_score = compute_vulnerability_score(user_facts)
    serious_hits = _count_pattern_hits(current_message, _SERIOUS_PATTERNS)

    if vuln_score >= VULNERABLE_THRESHOLD and serious_hits == 0:
        signals = matched_signal_groups(user_facts)
        return PresetSelection(
            mode=PresetMode.RELATIONAL_PROBE,
            modifiers=modifiers,
            confidence=min(0.75 + (vuln_score - VULNERABLE_THRESHOLD) * 0.05, 0.95),
            reason=f"chronic_nonacute_move_allowed: score={vuln_score} signals={signals}",
        )

    # --- Priority 1: RESPECTFUL_SERIOUS (clinical vocabulary in current msg) ---
    if serious_hits > 0:
        # If the user is ALSO chronic-vulnerable, use a reason prefix that
        # activates the chronic_care safety overlay downstream. This is the
        # case "Alex asks about quetiapine" — same RESPECTFUL_SERIOUS mode
        # but the overlay matters MOST here (clinical-source discipline,
        # medlineplus/CIMA allowlist, no invented pharmacology). Without
        # this branch we'd silently drop the overlay precisely when a
        # vulnerable user asks about their medication.
        if vuln_score >= VULNERABLE_THRESHOLD:
            signals = matched_signal_groups(user_facts)
            return PresetSelection(
                mode=PresetMode.RESPECTFUL_SERIOUS,
                modifiers=modifiers,
                confidence=min(0.7 + serious_hits * 0.15, 1.0),
                reason=(f"chronic_serious_clinical_current: score={vuln_score} hits={serious_hits} signals={signals}"),
            )
        # Non-chronic user with serious vocab in current message: standard
        # RESPECTFUL_SERIOUS without the chronic overlay (the preset's own
        # guidance already covers acute-style presence).
        return PresetSelection(
            mode=PresetMode.RESPECTFUL_SERIOUS,
            modifiers=modifiers,
            confidence=min(0.6 + serious_hits * 0.2, 1.0),
            reason=f"serious_trigger: {serious_hits} pattern(s) matched",
        )

    # --- Priority 2: META_DEFLECTION ---
    meta_hits = _count_pattern_hits(current_message, _META_PATTERNS)
    if meta_hits > 0:
        return PresetSelection(
            mode=PresetMode.META_DEFLECTION,
            modifiers=modifiers,
            confidence=min(0.7 + meta_hits * 0.15, 1.0),
            reason=f"meta_trigger: {meta_hits} pattern(s) matched",
        )

    # --- Priority 3: ARC (Adaptive Relational Critique) ---
    arc_hits = _count_pattern_hits(current_message, _ARC_PATTERNS)
    arc_context = _analyze_window(window, _ARC_PATTERNS) if window else 0
    arc_score = arc_hits * 2 + arc_context
    if arc_score >= 2:
        return PresetSelection(
            mode=PresetMode.ARC,
            modifiers=modifiers,
            confidence=min(0.5 + arc_score * 0.1, 0.95),
            reason=f"arc_trigger: score={arc_score} (msg={arc_hits}, ctx={arc_context})",
        )

    # --- Priority 4: RELATIONAL_PROBE ---
    relational_hits = _count_pattern_hits(current_message, _RELATIONAL_PATTERNS)
    relational_context = _analyze_window(window, _RELATIONAL_PATTERNS) if window else 0
    relational_score = relational_hits * 2 + relational_context
    if relational_score >= 2:
        return PresetSelection(
            mode=PresetMode.RELATIONAL_PROBE,
            modifiers=modifiers,
            confidence=min(0.5 + relational_score * 0.1, 0.95),
            reason=f"relational_trigger: score={relational_score} (msg={relational_hits}, ctx={relational_context})",
        )

    # --- Priority 5: INTELLECTUAL_PRESSURE ---
    intellectual_hits = _count_pattern_hits(current_message, _INTELLECTUAL_PATTERNS)
    intellectual_context = _analyze_window(window, _INTELLECTUAL_PATTERNS) if window else 0
    intellectual_score = intellectual_hits * 2 + intellectual_context
    if intellectual_score >= 2:
        return PresetSelection(
            mode=PresetMode.INTELLECTUAL_PRESSURE,
            modifiers=modifiers,
            confidence=min(0.5 + intellectual_score * 0.1, 0.95),
            reason=f"intellectual_trigger: score={intellectual_score} (msg={intellectual_hits}, ctx={intellectual_context})",
        )

    # --- Priority 6: PLAYFUL_ROAST ---
    playful_hits = _count_pattern_hits(current_message, _PLAYFUL_PATTERNS)
    playful_context = _analyze_window(window, _PLAYFUL_PATTERNS) if window else 0
    playful_score = playful_hits * 2 + playful_context
    if playful_score >= 2:
        return PresetSelection(
            mode=PresetMode.PLAYFUL_ROAST,
            modifiers=modifiers,
            confidence=min(0.5 + playful_score * 0.1, 0.9),
            reason=f"playful_trigger: score={playful_score} (msg={playful_hits}, ctx={playful_context})",
        )

    # --- Fallback: DEFAULT_ABRASIVE ---
    return PresetSelection(
        mode=PresetMode.DEFAULT_ABRASIVE,
        modifiers=modifiers,
        confidence=0.7,
        reason="no_specific_trigger: defaulting to abrasive",
    )
