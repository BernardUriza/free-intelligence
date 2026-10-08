"""The ONE addressing predicate — who is this message talking TO?

Two consumers MUST stay complements or the family breaks (P0 2026-07-06):
  - Insult's suppression gate (``personas/insult/cogs/chat/batch.py``): when a
    message addresses a sibling, Insult stays silent.
  - The sibling's summon gate (``persona_gateway/gateway.py``): when a message
    addresses THIS persona, it answers.

When the two gates evaluate DIFFERENT predicates, messages fall in the crack
between them: "si quieres dile a frugi que tienes ahorita…" (Bernard → Alex,
2026-07-06 17:24Z) matched Insult's bare ``\\bfrugi\\b`` scan (muted) but not the
gateway's mention-only rule (silent) — NOBODY answered for 5 minutes. Both
sides importing THIS module is the structural fix, not a convention.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Words that mark the alias as the OBJECT of the sentence — the user is talking
# ABOUT the persona to someone else, not TO it: "dile A frugi", "hablando DE
# frugi", "CON frugi". A vocative ("frugi, qué opinas" / "gracias frugi") has no
# object marker in front and IS an address.
ALIAS_OBJECT_MARKERS = frozenset({"a", "al", "de", "del", "con", "para", "sobre", "que"})

_HOST_NAME_PREFIX = re.compile(r"@?insult\b", re.IGNORECASE)


def opens_addressing_insult(text: str) -> bool:
    """True when the message OPENS by naming Insult (the host). The addressee is
    whoever HEADS the message: "insult, invita a alice" is a request TO Insult
    that merely names a sibling — Insult answers, the sibling stays out."""
    return _HOST_NAME_PREFIX.match((text or "").lstrip()) is not None


def alias_is_addressee(alias: str, text: str) -> bool:
    """True when ``alias`` appears as an ADDRESSEE (vocative) in ``text`` — at
    least one whole-word occurrence NOT preceded by an object marker.
    Occurrence-wise on purpose: "dile a frugi… frugi, contéstale tú" is object
    first, vocative second → still an address."""
    low = (text or "").lower()
    for match in re.finditer(rf"\b{re.escape(alias.lower())}\b", low):
        before = low[: match.start()].rstrip()
        prev_word = before.rsplit(None, 1)[-1] if before else ""
        if prev_word.strip(",:;¿?¡!.…") in ALIAS_OBJECT_MARKERS:
            continue
        return True
    return False


def any_alias_is_addressee(aliases: Iterable[str], text: str) -> bool:
    """True when ANY of ``aliases`` is vocatively addressed in ``text``."""
    return any(alias_is_addressee(a, text) for a in aliases if a)
