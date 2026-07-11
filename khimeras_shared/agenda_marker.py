"""Standing-agenda marker parser — `[AGENDA:]` extraction and stripping.

Shared text util (like `khimeras_shared/research_marker.py`): BOTH the plumbing
(Insult, `personas/insult`) and the gateway (siblings, `persona_gateway`) parse
this marker off a runner response, so it lives in `khimeras_shared` — never in a
persona package the gateway may not import.

Mirrors the `[RESEARCH:]` / `[INVITE:]` / `[REMIND:]` pipelines. The persona
emits `[AGENDA: <goal>]` when someone asks it to keep *continuous* watch over
something ("estáte al pendiente de X", "avísame si sale algo nuevo de Y"). A
durable standing agenda is then created; a proactive drain loop wakes the persona
on a cadence to pursue that goal on its own and post genuine novelty. This module
owns the in-band marker contract:

- `parse_agenda(text)`: extract the agenda goal (one per turn)
- `strip_agenda(text)`: remove the markers before sending to Discord

Why a marker and not a structured tool call: every persona turn runs on the
persona-runner and `AgentRunnerClient` returns `tool_calls=[]`, so a caller-side
tool definition can never fire from a runner turn. Markers are the canonical
in-band channel for runner→caller intents (`[REACT:]`, `[REMEMBER:]`,
`[INVITE:]`, `[REMIND:]`, `[RESEARCH:]`); this extends the same contract to
durable standing agendas.
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger()

AGENDA_PATTERN = re.compile(r"\[AGENDA:([^\]]*)\]", re.IGNORECASE)

__all__ = ["AGENDA_PATTERN", "parse_agenda", "strip_agenda"]


def parse_agenda(text: str) -> str | None:
    """Extract the agenda goal from the FIRST `[AGENDA:...]` marker.

    One agenda per turn: a second marker in the same response is a model
    stutter, not two agendas — parsing them all would double-create. Returns
    None when no marker is present or the goal is empty after strip.
    """
    if not text or "[AGENDA:" not in text.upper():
        return None
    for match in AGENDA_PATTERN.finditer(text):
        goal = (match.group(1) or "").strip()
        if not goal:
            continue
        return goal
    return None


def strip_agenda(text: str) -> str:
    """Remove all `[AGENDA:...]` markers from the response text.

    Same conservative cleanup as `strip_research`: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not text:
        return text
    cleaned = AGENDA_PATTERN.sub("", text)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
