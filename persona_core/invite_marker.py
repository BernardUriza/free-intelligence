"""Sibling-summon marker — `[INVITE:]` extraction and stripping.

This is the module the rest of the marker family has been citing as its own
model since the demux: `research_marker` documents "same conservative cleanup as
`strip_invites`", `agenda_marker` says it "mirrors the `[INVITE:]` pipeline".
Both were describing code that lived in `personas/insult/cogs/chat/invites.py`
and **died with `personas/` in the 2026-07-14 purge**. Nothing replaced it, so
`[INVITE:]` became the one marker in the family with no parser and no stripper.

The cost was not cosmetic. On 2026-07-31, after Bernard said he had thought
about suicide that day, Insult emitted the marker as its DNA instructs — and
because nothing stripped it, Discord rendered the raw internal note to HIM:

    [INVITE: Bern acaba de decir "he pensado en el suicidio hoy" — ideación
    presente en este día. Yo estoy con él sosteniendo, pero necesita tu registro
    también, no solo mi filo. Entra suave.]

A note written ABOUT him, TO another persona, quoting his own disclosure back at
him in the third person, at the worst possible moment. And ALICE never arrived,
because the summon had no parser either.

So this module is deliberately paranoid in one direction: **stripping is
unconditional**. Even if the summon fails, is disabled, or nobody wires the
parser at all, the marker must never reach a human — that failure mode has a
real victim and it already happened once.

Contract, mirroring the sibling markers exactly (Art. 6):
- `parse_invite(text)`: the reason for the FIRST marker (one summon per turn)
- `strip_invites(text)`: remove every marker before the text reaches Discord
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger()

INVITE_PATTERN = re.compile(r"\[INVITE:([^\]]*)\]", re.IGNORECASE)

__all__ = ["INVITE_PATTERN", "parse_invite", "strip_invites"]


def parse_invite(text: str) -> str | None:
    """Extract the summon reason from the FIRST `[INVITE:...]` marker.

    One summon per turn: the DNA says "never more than ONE `[INVITE:]` per
    response", so a second marker is a model stutter, not a second sibling.
    Returns None when no marker is present or the reason is empty after strip.
    """
    if not text or "[INVITE:" not in text.upper():
        return None
    for match in INVITE_PATTERN.finditer(text):
        reason = (match.group(1) or "").strip()
        if not reason:
            continue
        return reason
    return None


def strip_invites(text: str) -> str:
    """Remove all `[INVITE:...]` markers from the response text.

    Same conservative cleanup as the sibling markers: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not text:
        return text
    cleaned = INVITE_PATTERN.sub("", text)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
