"""Ops surface — liveness and session reset.

`/health` is PUBLIC and always 200: it is a liveness probe, not a readiness gate
(coupling the pod's restart decision to a downstream is how a 30s blip becomes an
outage). The body carries the honest state for monitoring — never a bare "ok"
that a dead runner could also return.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header

from persona_runner.core import config
from persona_runner.core.auth import check_auth
from persona_runner.engine import session_pool

log = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Public liveness probe. Always 200. Body reflects state for monitoring."""
    claude_md_path = config.WORKSPACE_ROOT / "CLAUDE.md"
    return {
        "status": "ok",
        "service": "persona-runner",
        "workspace_present": config.WORKSPACE_ROOT.exists(),
        "persona_present": config.PERSONA_PATH.exists(),
        "claude_md_present": claude_md_path.exists(),
        "auth_configured": bool(config.RUNNER_AUTH_TOKEN),
        "model": config.DEFAULT_MODEL,
        "open_sessions": session_pool.pool_size(),
    }


@router.delete("/v1/session/{channel_id}")
async def reset_session(channel_id: str, authorization: str | None = Header(default=None)) -> dict:
    """Force-close a channel's long-lived SDK sessions — every persona's.

    The next `/v1/turn` re-creates a fresh session: new session_uuid, no prior
    turn history, persona + CLAUDE.md re-cached on the first turn. Idempotent:
    a channel with nothing open returns `existed=false` and does not raise.

    Use when a session is stuck in a wrong belief (a tool call failed and the
    agent now thinks the tool does not exist, a confabulated fact got baked in).
    Without it the only options were waiting for the reaper or moving channels.

    Discovered 2026-05-19 during the F+C smoke test: a `publish_html_artifact`
    call failed (missing table); from then on the agent insisted the tool was
    unavailable even after the table existed. The poisoned belief lived as long
    as the client did.

    Closes EVERY persona's slot in the channel (2026-07-14): a channel now hosts
    Insult + siblings, and the old implementation force-closed only the bare
    `channel_id` key — a stuck Vultur session survived the reset in silence.
    """
    check_auth(authorization)
    closed = await session_pool.close_channel(channel_id)
    log.info(
        "agent_runner_session_reset",
        channel_id=channel_id,
        existed=bool(closed),
        closed_keys=closed,
        pool_size=session_pool.pool_size(),
    )
    return {
        "channel_id": channel_id,
        "existed": bool(closed),
        "closed_keys": closed,
        "pool_size": session_pool.pool_size(),
    }
