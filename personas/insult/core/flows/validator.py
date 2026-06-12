"""Post-generation validator — logs when the response diverged from the plan.

Runs AFTER the LLM produced output. Compares the realized response
against what the flow plan demanded (shape length bounds, probing
requires ?, pressure-1 forbids hostility, repetition-loop forbids
long replies). Records violations but does NOT block delivery — this
is a soft-monitoring signal for drift analysis, not a gate.

F2 (2026-05-11) adds `detect_lifelessness` — a 6-signal check for
replies that are competent-but-flat: acknowledgment without movement,
courtesy follow-up without tension, therapy-speak vocabulary, literal
reflection without sharpening. Same soft-monitor contract as the rest
of this module: logs only, no blocking, no retry. The score lets us
measure if the 'flat presence' problem (the Alex DIF turn) exists at
scale before we change behavior in F3+."""

from __future__ import annotations

import re

import structlog

from personas.insult.core.flows.patterns import HOSTILE_PATTERNS, STOPWORDS, count_hits
from personas.insult.core.flows.types import (
    ConversationPattern,
    FlowAnalysis,
    ResponseShape,
)

log = structlog.get_logger()


def validate_flow_adherence(response: str, analysis: FlowAnalysis) -> dict:
    """Compare realized response to the flow plan. Returns a dict of
    violations + adherence score. Logged, not enforced."""
    word_count = len(response.split())
    sentence_count = len([s for s in re.split(r"[.!?]+", response) if s.strip()])
    question_count = response.count("?")

    violations: list[str] = []

    shape = analysis.expression.selected_shape
    if shape == ResponseShape.ONE_HIT and sentence_count > 2:
        violations.append(f"one_hit_but_{sentence_count}_sentences")
    elif shape == ResponseShape.DENSE_CRITIQUE and word_count < 30:
        violations.append(f"dense_critique_but_{word_count}_words")
    elif shape == ResponseShape.PROBING and question_count == 0:
        violations.append("probing_but_no_questions")

    if analysis.pressure.pressure_level == 1:
        hostile_hits = count_hits(response, HOSTILE_PATTERNS)
        if hostile_hits > 0:
            violations.append(f"pressure_1_but_aggressive_hits={hostile_hits}")

    if analysis.awareness.detected_pattern == ConversationPattern.REPETITION_LOOP and word_count > 50:
        violations.append(f"repetition_loop_but_long_response_{word_count}")

    adherence = {
        "shape_planned": shape.value,
        "flavor_planned": analysis.expression.selected_flavor.value,
        "response_word_count": word_count,
        "response_sentence_count": sentence_count,
        "response_question_count": question_count,
        "violations": violations,
        "adherence_score": max(0.0, 1.0 - len(violations) * 0.25),
    }

    if violations:
        log.info("flow_adherence_violation", **adherence)

    return adherence


# ═══════════════════════════════════════════════════════════════════════════
# F2: Lifelessness detection — soft-monitoring for "competent but flat"
# ═══════════════════════════════════════════════════════════════════════════
#
# The Alex DIF turn that triggered F1+F2: bot replied
#
#   "Que te den la tarjeta sin drama, nada más eso. Y lo del DIF — a veces
#    los sistemas de evaluación te encasillan... Mañana nos cuentas."
#
# Not wrong. Not insulting. Validates the user's experience. Closes with a
# follow-up. And yet — it sounds like a support volunteer. It acknowledges
# without moving. It mirrors without sharpening. It ends with care-staff
# language ("mañana nos cuentas") that performs presence without taking
# any conversational risk.
#
# These regexes target the linguistic shape of that flatness. The detector
# is soft-monitor only in F2: we want to measure how often this happens at
# scale before we decide whether F3 should retry-on-lifelessness.

# Signal 1: opens with acknowledgment-only language
# (the response leads with "claro / entiendo / tiene sentido" — fine in
# isolation, but a tell that the reply will not move past the user's frame).
_ACKNOWLEDGMENT_OPENER_RE = re.compile(
    r"(?im)^\s*("
    r"claro,?|entiendo,?|tiene sentido,?|qu[eé] buena pregunta,?|interesante,?|"
    r"comprendo,?|of course,?|i (understand|see|get it),?|that makes sense,?|"
    r"good question,?|fair (point|enough),?"
    r")\b"
)

# Signal 2: closes with a courtesy follow-up that defers movement to later
# (the "mañana nos cuentas / cómo te fue / déjame saber / aquí estoy" tell.
# These phrases are warm but they are explicitly NOT a move — they pass the
# baton back to the user instead of doing the conversational work now).
_COURTESY_FOLLOWUP_CLOSE_RE = re.compile(
    r"(?i)("
    r"ma[nñ]ana (me )?cuentas|c[oó]mo te (fue|va)|d[eé]jame saber|"
    r"aqu[ií] estoy|ya nos cuentas|nos cuentas (luego|despu[eé]s|ma[nñ]ana)|"
    r"avisa(me)? (luego|despu[eé]s|c[oó]mo)|cu[eé]ntame c[oó]mo|"
    # English: "let me know how it goes", "tell me how it went", "keep me posted".
    # `let me know` must be followed by either an end-anchor or `how it goes|went`
    # (bare `let me know` mid-sentence is not a courtesy close).
    r"let me know( how it (goes|went))?|keep me posted|"
    r"tell me how it (goes|went)|how it (goes|went)"
    r")[.!?\s]*$"
)

# Signal 3: therapy-speak vocabulary
# (the language of professional empathy templates. Each phrase below
# performs care instead of doing it. Threshold of 2 hits = flag.)
_THERAPY_SPEAK_PATTERNS = [
    re.compile(r"(?i)\b(es )?v[aá]lido( sentir| que sientas)?\b"),
    re.compile(r"(?i)\bvalidar (tus|sus) (emociones|sentimientos|experiencias)\b"),
    re.compile(r"(?i)\best[aá] bien sentir(se)?\b"),
    re.compile(r"(?i)\bno est[aá]s solo[ax]?\b"),
    re.compile(r"(?i)\btus (emociones|sentimientos) son\b"),
    re.compile(r"(?i)\bt[oó]mate (tu )?tiempo\b"),
    re.compile(r"(?i)\bdate (el )?permiso\b"),
    re.compile(r"(?i)\bhonra (tu|tus)\b"),
    re.compile(r"(?i)\b(your|tus) (feelings|emotions) (are valid|son v[aá]lid)"),
    re.compile(r"(?i)\bit'?s (ok|okay) to feel\b"),
    re.compile(r"(?i)\byou'?re not alone\b"),
    re.compile(r"(?i)\bsea lo que sea que (sientes|estes sintiendo)\b"),
]

# Signal 4: structural words that indicate the reply IS doing a move
# (presence of any of these is evidence AGAINST lifelessness — used to
# soften the score on borderline cases. NOT a positive signal on its own.)
_MOVEMENT_MARKERS_RE = re.compile(
    r"(?i)\b("
    # Pivots that introduce a new framing
    r"pero|aunque|sin embargo|however|though|"
    # Sententia-style framings ("lo culero es", "lo raro es", "el problema es")
    r"lo (culero|raro|jodido|chistoso|interesante|extra[ñn]o|loco) es\b|"
    r"el problema (real|de fondo) (es|no es)|"
    # Tension-naming: explicitly the UNSAID, the AVOIDED, the HIDDEN
    r"lo que no dices|lo que evitas|lo que est[aá]s evitando|"
    r"lo que (en realidad )?(temes|escondes|callas)|"
    # Structural critique vocabulary
    r"el sistema (te |no )|burocr[aá]tic|"
    r"contradicci[oó]n|tensi[oó]n irresuelta|"
    # Consequential questions and direct prompts (rare end-anchored markers)
    r"specifically what|specifically,?\s|"
    r"y a ti qu[eé]|qu[eé] (vas a hacer|harías|crees que de verdad|esperas (de verdad|tú))"
    r")\b"
)

# Signal 5: words from the user's last message that the bot can sharpen
# instead of mirror. We compute a Jaccard-like content-word overlap between
# the user's last 60 words and the response's first 60 words. High overlap
# without movement markers ≈ reflection without sharpening.
_LITERAL_REFLECTION_OVERLAP_THRESHOLD = 0.4


def _content_words(text: str, *, limit: int = 60) -> set[str]:
    """Lowercase content words, stopwords removed, truncated to `limit` tokens.

    Stopwords reused from flows.patterns.STOPWORDS for consistency with
    the awareness analyzer's repetition-loop detector."""
    tokens = re.findall(r"\b[\wáéíóúñü]+\b", text.lower())[:limit]
    return {t for t in tokens if t not in STOPWORDS and len(t) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def detect_lifelessness(response: str, user_message: str = "") -> dict:
    """Score how 'competent-but-flat' the response reads.

    Returns a dict with `score` (0-6), `signals` (list of which fired),
    and convenience flags for KQL filtering. Soft-monitor only — caller
    is expected to log and NOT block delivery. F2 contract.

    Scoring:
        0   alive
        1   minor signal (one weak tell)
        2   warning band (two tells — review in aggregate)
        3+  flat band (target of any future retry policy)

    Movement markers cancel one signal — a response that contains
    "pero el sistema...", "lo culero es...", or names a tension is
    judged less flat even if it opens with acknowledgment.
    """
    text = response or ""
    signals: list[str] = []

    has_acknowledgment_opener = bool(_ACKNOWLEDGMENT_OPENER_RE.search(text))
    has_courtesy_close = bool(_COURTESY_FOLLOWUP_CLOSE_RE.search(text))
    therapy_speak_hits = sum(1 for p in _THERAPY_SPEAK_PATTERNS if p.search(text))
    has_movement_markers = bool(_MOVEMENT_MARKERS_RE.search(text))
    has_question = "?" in text

    # Signal 5: literal reflection (overlap with user message without movement)
    reflection_overlap = 0.0
    if user_message:
        reflection_overlap = _jaccard(_content_words(user_message), _content_words(text))
    has_literal_reflection = reflection_overlap >= _LITERAL_REFLECTION_OVERLAP_THRESHOLD and not has_movement_markers

    # Signal 6: no question + no movement markers + no tension named
    # (composite signal — the reply does not push, probe, or sharpen).
    has_no_pull = not has_question and not has_movement_markers

    if has_acknowledgment_opener:
        signals.append("acknowledgment_opener")
    if has_courtesy_close:
        signals.append("courtesy_followup_close")
    if therapy_speak_hits >= 2:
        signals.append(f"therapy_speak_{therapy_speak_hits}")
    if has_literal_reflection:
        signals.append(f"literal_reflection_{reflection_overlap:.2f}")
    if has_no_pull:
        signals.append("no_question_no_movement")

    score = len(signals)
    # Movement markers cancel one signal (max once).
    if has_movement_markers and score > 0:
        score -= 1

    return {
        "score": score,
        "signals": signals,
        "has_acknowledgment_opener": has_acknowledgment_opener,
        "has_courtesy_close": has_courtesy_close,
        "therapy_speak_hits": therapy_speak_hits,
        "has_movement_markers": has_movement_markers,
        "reflection_overlap": round(reflection_overlap, 3),
        "has_question": has_question,
        # KQL convenience: a single field that buckets the response.
        # 0-1 → "alive", 2 → "tibia", 3+ → "flat".
        "band": "alive" if score <= 1 else ("tibia" if score == 2 else "flat"),
    }
