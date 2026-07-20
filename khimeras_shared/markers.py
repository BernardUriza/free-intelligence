"""In-band marker utilities shared across turn and drain paths.

Two responsibilities live here:

1. `[REMIND_CANCEL:]` — parse + strip for the reminder-cancellation marker. The
   persona emits `[REMIND_CANCEL: <criterio>]` when the user asks to drop a
   pending reminder; the criterion is matched as a case-insensitive substring
   against the PENDING reminders of the same user + persona (see
   `RemindersRepository.cancel_pending`). Parsing lives beside the strip
   composer so every deferred path inherits the strip for free.

2. `strip_delivery_markers` — strip every in-band marker before a DEFERRED
   delivery. A live turn parses each marker and ACTS on it (applies `[REACT:]`,
   queues `[RESEARCH:]`, saves `[AGENDA:]`) then strips it. But a DEFERRED post —
   a research report or an agenda finding a drain loop delivers minutes later —
   has no live turn: there is no fresh user message to react to, and re-queueing
   its own marker would loop. So a deferred delivery must STRIP every marker
   (never leak a raw `[REACT:🌸]` as visible text — the 2026-07-11 bug Bernard
   caught in Alice's report).

Composing all the shared strips in one place means the next marker added can't
re-leak from a deferred path: add its strip here and every drain loop inherits it.
"""

from __future__ import annotations

import re

from khimeras_shared.agenda_marker import strip_agenda
from khimeras_shared.reactions import strip_reactions
from khimeras_shared.remember_marker import strip_remembers
from khimeras_shared.remind_marker import strip_reminds
from khimeras_shared.research_marker import strip_research

__all__ = [
    "MAX_CANCEL_CRITERION_LEN",
    "REMIND_CANCEL_PATTERN",
    "parse_remind_cancels",
    "strip_delivery_markers",
    "strip_remind_cancels",
]

REMIND_CANCEL_PATTERN = re.compile(r"\[REMIND_CANCEL:([^\]]*)\]", re.IGNORECASE)
MAX_CANCEL_CRITERION_LEN = 200


def parse_remind_cancels(response: str) -> list[str]:
    """Extract every cancellation criterion from `[REMIND_CANCEL: <criterio>]`.

    Unlike `parse_remind` (one per turn — a duplicate would double-schedule),
    multiple cancel markers are legitimate: each criterion targets a different
    pending reminder, and cancelling is idempotent so a stutter costs nothing.
    Duplicated criteria are deduped (case-insensitive); empty bodies are skipped
    — an empty substring would match EVERY pending reminder, which is a
    cancel-all the persona never asked for.
    """
    if not response or "[REMIND_CANCEL:" not in response.upper():
        return []
    criteria: list[str] = []
    seen: set[str] = set()
    for match in REMIND_CANCEL_PATTERN.finditer(response):
        criterion = (match.group(1) or "").strip()
        if not criterion:
            continue
        if len(criterion) > MAX_CANCEL_CRITERION_LEN:
            criterion = criterion[:MAX_CANCEL_CRITERION_LEN].rstrip()
        key = criterion.lower()
        if key in seen:
            continue
        seen.add(key)
        criteria.append(criterion)
    return criteria


def strip_remind_cancels(response: str) -> str:
    """Remove all `[REMIND_CANCEL:...]` markers from the response text.

    Same conservative cleanup as `strip_reminds`: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not response:
        return response
    cleaned = REMIND_CANCEL_PATTERN.sub("", response)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def strip_delivery_markers(text: str) -> str:
    """Remove ALL in-band markers from text about to be delivered with no live
    turn to act on them. Order-independent (each strip targets its own marker).

    `strip_remind_cancels` runs BEFORE `strip_reminds` by construction anyway,
    but the two patterns cannot collide: `[REMIND:` requires the colon right
    after REMIND, `[REMIND_CANCEL:` has the underscore in between.
    """
    return strip_remembers(
        strip_reminds(strip_remind_cancels(strip_agenda(strip_research(strip_reactions(text or "")))))
    ).strip()
