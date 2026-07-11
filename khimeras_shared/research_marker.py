"""Deep-research marker parser — `[RESEARCH:]` extraction and stripping.

Shared text util (like `khimeras_shared/reactions.py`): BOTH the plumbing
(Insult, `personas/insult`) and the gateway (siblings, `persona_gateway`) parse
this marker off a runner response, so it lives in `khimeras_shared` — never in a
persona package the gateway may not import.

Mirrors the `[INVITE:]` / `[REMIND:]` pipelines. The persona emits
`[RESEARCH: <prompt>]` when it accepts a heavy research request; a durable worker
runs the job later and posts the result back. This module owns the in-band marker
contract:

- `parse_research(text)`: extract the research prompt (one per turn)
- `strip_research(text)`: remove the markers before sending to Discord

Why a marker and not a structured tool call: every persona turn runs on the
persona-runner and `AgentRunnerClient` returns `tool_calls=[]`, so a caller-side
tool definition can never fire from a runner turn. Markers are the canonical
in-band channel for runner→caller intents (`[REACT:]`, `[REMEMBER:]`,
`[INVITE:]`, `[REMIND:]`); this extends the same contract to durable research jobs.
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger()

RESEARCH_PATTERN = re.compile(r"\[RESEARCH:([^\]]*)\]", re.IGNORECASE)

__all__ = ["RESEARCH_PATTERN", "parse_research", "strip_research"]


def parse_research(text: str) -> str | None:
    """Extract the research prompt from the FIRST `[RESEARCH:...]` marker.

    One job per turn: a second marker in the same response is a model stutter,
    not two jobs — parsing them all would double-queue. Returns None when no
    marker is present or the prompt is empty after strip.
    """
    if not text or "[RESEARCH:" not in text.upper():
        return None
    for match in RESEARCH_PATTERN.finditer(text):
        prompt = (match.group(1) or "").strip()
        if not prompt:
            continue
        return prompt
    return None


def strip_research(text: str) -> str:
    """Remove all `[RESEARCH:...]` markers from the response text.

    Same conservative cleanup as `strip_invites`: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not text:
        return text
    cleaned = RESEARCH_PATTERN.sub("", text)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
