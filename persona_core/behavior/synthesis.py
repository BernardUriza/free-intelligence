"""Detect cross-domain conceptual synthesis in a user message.

Phase 2.5 (v3.6.3): when the user articulates a connection between two
domains the bot was not explicitly trained to compare (e.g. apartheid ↔
speciesism, neoliberalism ↔ self-help culture, biopolitics ↔ urban
planning), the right move is to LEARN before challenging. The earlier
behavior — DEFAULT_ABRASIVE responding "qué tiene que ver tu dieta" or
arc/memory_recall conceding vaguely "hay algo ahí" — fails the user
who is reaching for genuine intellectual exchange.

This module is the trigger detector. It runs over the current message
(plus a short look-back) and returns a saliency score. The caller in
``presets.classify_preset`` decides whether to attach the
``MULTI_DOMAIN_SYNTHESIS`` modifier based on the score.

Pure heuristic — zero LLM cost. Tuned to favor recall over precision:
a false positive costs one web_search ($0.01); a false negative is the
exact bug the user reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Pattern groups
# ---------------------------------------------------------------------------
#
# STRONG patterns are explicit cross-domain comparisons that need almost no
# context to interpret. One match is enough to fire the modifier.
#
# WEAK patterns are softer signals (academic vocabulary, abstract noun-of-X
# constructions). At least two are needed to fire the modifier on their own.
#
# COUNTER patterns suppress firing — humor markers, throwaway quips that
# happen to use comparison vocabulary without intent ("X y Y son lo mismo,
# jajaja"). One counter match drops the activation level by one tier.

_STRONG = [
    # Explicit "two sides of the same coin" / "same logic" constructions
    re.compile(r"(?i)\b(dos|two)\s+caras?\s+de\s+(la|una|the|a)\s+(misma|same)\b"),
    re.compile(r"(?i)\b(la\s+)?misma\s+(l[oó]gica|estructura|ra[íi]z|moneda|cosa|operaci[oó]n)\b"),
    re.compile(r"(?i)\bsame\s+(logic|structure|root|coin|principle|operation)\b"),
    # Explicit equation / parallel
    re.compile(r"(?i)\b(es|son)\s+(esencialmente|fundamentalmente|en el fondo|in essence)\s+(lo mismo|the same)\b"),
    re.compile(r"(?i)\b(parallel|paralelo)\s+entre\s+\w+\s+y\s+\w+\b"),
    # Pairs of -ism nouns. Allow optional articles between the two terms
    # ("veganismo y EL feminismo") and accept English "racism" (3-char prefix
    # + ism) without losing precision — short -isms like "rac/sex/age + ism"
    # are all genuine theoretical vocabulary.
    re.compile(
        r"(?i)\b([a-záéíóúñ]{4,}ismo)\s+(?:y|e|vs?\.?|and|versus)\s+(?:el\s+|la\s+|los\s+|las\s+|the\s+)?([a-záéíóúñ]{4,}ismo)\b"
    ),
    re.compile(r"(?i)\b([a-z]{3,}ism)\s+(?:and|vs?\.?|y)\s+(?:the\s+|el\s+|la\s+)?([a-z]{3,}ism)\b"),
    # "discrimina(ción) ... ismo" or vice versa — cross-discrimination framing
    re.compile(r"(?i)\bdiscriminac?i[oó]n\s+\w*\s*(racial|de\s+especie|por\s+especie)\b"),
]

_WEAK = [
    # Comparison openers that often introduce conceptual links
    re.compile(r"(?i)\b(es\s+como|son\s+como|like|akin\s+to|guarda(n)?\s+relaci[oó]n)\b"),
    re.compile(r"(?i)\bse\s+parece\s+(a|al|mucho a)\b"),
    re.compile(r"(?i)\b(an[aá]logo|analogous|equivalente|equivalent)\s+(a|al|to)\b"),
    # Academic / theoretical openers ("la lógica del", "el principio de", "la estructura")
    re.compile(r"(?i)\b(la|el)\s+(l[oó]gica|estructura|principio|naturaleza|ra[íi]z|ontolog[íi]a)\s+(de|del)\b"),
    re.compile(r"(?i)\bthe\s+(logic|structure|principle|nature|root|ontology)\s+of\b"),
    # Single -ism / -ismo word in a message of meaningful length (signals theoretical vocabulary)
    re.compile(r"(?i)\b[a-záéíóúñ]{6,}ismo\b"),
    re.compile(r"(?i)\b[a-z]{6,}ism\b"),
    # Marquee theorists / canonical pairings — when their names appear, the
    # user is signaling "I want literature, not vibes". Keep this list short
    # and unambiguous; broaden carefully.
    re.compile(r"(?i)\b(Singer|Foucault|Adorno|Marx|Patterson|Fanon|hooks|Said|Spivak|Butler|Federici)\b"),
    # Citation-style framings — "como X argumenta", "según Y", "as Z says"
    # signal the user wants the bot to engage with named literature, not
    # opinion. Generic enough to apply across domains.
    re.compile(
        r"(?i)\b(como|seg[uú]n|de acuerdo a|as|according to)\s+[A-Z][a-záéíóúñ]+\s+(argument|dice|escribe|sostiene|argues|writes|claims|points)"
    ),
]

_COUNTERS = [
    # Levity markers that drain seriousness
    re.compile(r"(j[aeíoóu]){2,}", re.IGNORECASE),  # jaja, jeje, jojo
    re.compile(r"(?i)\b(lol|lmao|xd|jaja|broma|bromita|cotorreando)\b"),
    # Trailing emojis that imply not-serious tone
    re.compile(r"[😂🤣😆😅🙃😜🤪]"),
]

# Minimum message length below which we don't bother — short messages can't
# carry a real synthesis claim, only a glib equation that's better handled
# by DEFAULT_ABRASIVE.
_MIN_MESSAGE_LENGTH = 30


@dataclass(frozen=True)
class SynthesisSignal:
    """Result of running the detector on a single message."""

    activated: bool
    strong_hits: int
    weak_hits: int
    counter_hits: int
    matched_terms: list[str]

    @property
    def reason(self) -> str:
        return (
            f"strong={self.strong_hits} weak={self.weak_hits} "
            f"counters={self.counter_hits} terms={self.matched_terms[:5]}"
        )


def _matches(patterns: list[re.Pattern[str]], text: str) -> tuple[int, list[str]]:
    hits = 0
    matched: list[str] = []
    for pat in patterns:
        m = pat.search(text)
        if m:
            hits += 1
            matched.append(m.group(0)[:40])
    return hits, matched


def detect_synthesis(current_message: str) -> SynthesisSignal:
    """Score the current message for cross-domain synthesis intent.

    Activation rules (recall over precision — false positives cost one
    web_search call, false negatives cost user trust):

    - Below ``_MIN_MESSAGE_LENGTH``: never activate.
    - At least one STRONG match → activate.
    - Two or more WEAK matches → activate.
    - One COUNTER match drops the effective tier: STRONG-only fire still
      activates (counters cannot suppress an explicit "dos caras de"); but
      a WEAK-only fire is suppressed by any counter.
    """
    if len(current_message) < _MIN_MESSAGE_LENGTH:
        return SynthesisSignal(False, 0, 0, 0, [])

    strong_hits, strong_matched = _matches(_STRONG, current_message)
    weak_hits, weak_matched = _matches(_WEAK, current_message)
    counter_hits, _ = _matches(_COUNTERS, current_message)

    matched = strong_matched + weak_matched

    if strong_hits >= 1:
        # Explicit comparison wins regardless of levity counters.
        return SynthesisSignal(True, strong_hits, weak_hits, counter_hits, matched)

    if weak_hits >= 2 and counter_hits == 0:
        return SynthesisSignal(True, strong_hits, weak_hits, counter_hits, matched)

    return SynthesisSignal(False, strong_hits, weak_hits, counter_hits, matched)
