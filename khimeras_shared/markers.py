"""Strip every in-band marker before a DEFERRED delivery.

A live turn parses each marker and ACTS on it (applies `[REACT:]`, queues
`[RESEARCH:]`, saves `[AGENDA:]`) then strips it. But a DEFERRED post — a research
report or an agenda finding a drain loop delivers minutes later — has no live
turn: there is no fresh user message to react to, and re-queueing its own marker
would loop. So a deferred delivery must STRIP every marker (never leak a raw
`[REACT:🌸]` as visible text — the 2026-07-11 bug Bernard caught in Alice's report).

Composing all the shared strips in one place means the next marker added can't
re-leak from a deferred path: add its strip here and every drain loop inherits it.
"""

from __future__ import annotations

from khimeras_shared.agenda_marker import strip_agenda
from khimeras_shared.reactions import strip_reactions
from khimeras_shared.remember_marker import strip_remembers
from khimeras_shared.remind_marker import strip_reminds
from khimeras_shared.research_marker import strip_research

__all__ = ["strip_delivery_markers"]


def strip_delivery_markers(text: str) -> str:
    """Remove ALL in-band markers from text about to be delivered with no live
    turn to act on them. Order-independent (each strip targets its own marker)."""
    return strip_remembers(strip_reminds(strip_agenda(strip_research(strip_reactions(text or ""))))).strip()
