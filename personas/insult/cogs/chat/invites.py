"""Sibling-summon marker parser — `[INVITE:]` extraction, stripping, firing.

Mirrors the `[REMEMBER:]` pipeline in `remembers.py`. The persona emits
`[INVITE: <reason>]` when it decides ALICE should take a turn in the channel.
This module:

- `parse_invite(text)`: extract the invite reason (one invite per turn)
- `strip_invites(text)`: remove the markers before sending to Discord
- `fire_invite(reason, ...)`: POST the persona gateway's `/invite` via
  `execute_invoke_alice`, best-effort in the background

Why a marker and not a structured tool call: with `LEGACY_LLM_ENABLED=false`
every Insult turn runs on the persona-runner (a Claude Code agent whose tool
universe is its own), and `AgentRunnerClient` returns `tool_calls=[]` — so the
legacy `invoke_alice` tool can never fire from a runner turn. Markers are the
canonical in-band channel for runner→plumbing intents (`[REACT:]`,
`[REMEMBER:]`); this extends the same contract to summoning a sibling.
"""

from __future__ import annotations

import re

import structlog

log = structlog.get_logger()

INVITE_PATTERN = re.compile(r"\[INVITE:([^\]]*)\]", re.IGNORECASE)
MAX_REASON_LEN = 500


def parse_invite(response: str) -> str | None:
    """Extract the summon reason from the FIRST `[INVITE:...]` marker.

    One invite per turn: a second marker in the same response is a model
    stutter, not two summons — parsing them all would double-post ALICE.
    Returns None when no marker is present or the reason is empty.
    """
    if not response or "[INVITE:" not in response.upper():
        return None
    for match in INVITE_PATTERN.finditer(response):
        reason = (match.group(1) or "").strip()
        if not reason:
            continue
        if len(reason) > MAX_REASON_LEN:
            reason = reason[:MAX_REASON_LEN].rstrip() + "…"
        return reason
    return None


def strip_invites(response: str) -> str:
    """Remove all `[INVITE:...]` markers from the response text.

    Same conservative cleanup as `strip_remembers`: removes the marker and
    collapses the multi-space / multi-newline holes the removal leaves.
    """
    if not response:
        return response
    cleaned = INVITE_PATTERN.sub("", response)
    cleaned = re.sub(r"  +", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


async def fire_invite(
    reason: str,
    *,
    channel_id: str,
    guild_id: str | None,
    channel_name: str | None,
) -> bool:
    """POST the gateway `/invite` for this channel. Best-effort: failures are
    logged, never raised — the user-visible turn already delivered."""
    from personas.insult.core.alice_tool import execute_invoke_alice

    try:
        ok = await execute_invoke_alice(
            {"reason": reason},
            channel_id=channel_id,
            guild_id=guild_id,
            channel_name=channel_name,
        )
    except Exception:
        log.exception("invite_marker_fire_failed", channel_id=channel_id, reason_preview=reason[:80])
        return False
    log.info(
        "invite_marker_fired",
        channel_id=channel_id,
        accepted=ok,
        reason_preview=reason[:80],
    )
    return ok
