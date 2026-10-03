"""Ops surface — liveness and session reset.

`/health` is PUBLIC and always 200: it is a liveness probe, not a readiness gate
(coupling the pod's restart decision to a downstream is how a 30s blip becomes an
outage). The body carries the honest state for monitoring — never a bare "ok"
that a dead runner could also return.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from persona_runner.core import config, readiness
from persona_runner.core.auth import check_auth
from persona_runner.engine import aire_route, auth_failure

log = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Public liveness probe. Always 200. Body reflects state for monitoring."""
    claude_md_path = config.WORKSPACE_ROOT / "CLAUDE.md"
    # A configured token proves a string was injected, never that upstream still
    # accepts it. `credentials_rejected` is the only field here that reflects a
    # REAL turn's verdict — the 2026-08-03 outage had every other field green
    # while no persona could answer anyone.
    rejected = auth_failure.last_failure()
    return {
        "status": "degraded" if rejected else "ok",
        "credentials_rejected": rejected,
        "service": "persona-runner",
        "workspace_present": config.WORKSPACE_ROOT.exists(),
        "persona_present": config.PERSONA_PATH.exists(),
        "claude_md_present": claude_md_path.exists(),
        "auth_configured": bool(config.RUNNER_AUTH_TOKEN),
        "model": config.DEFAULT_MODEL,
    }


@router.get("/ready")
async def ready() -> JSONResponse:
    """Public readiness probe: 503 until the turn pipeline is warm (or capped).

    Never touches a downstream — it reads a flag `core/readiness.gate` sets once
    and never clears. Target of the readiness probe declared in
    `scripts/cd_runner_template.py`; `/health` stays the always-200 liveness
    and startup target.
    """
    body = readiness.state()
    return JSONResponse(body, status_code=200 if body["ready"] else 503)


@router.delete("/v1/session/{channel_id}")
async def reset_session(channel_id: str, authorization: str | None = Header(default=None)) -> dict:
    """Force a fresh AIRE session for a channel — every persona's casita.

    A poisoned belief lives in the AIRE session's transcript, and the session is
    the TOPIC (engine/aire_topic): dropping the channel's durable topic rows
    makes each casita's next turn mint a fresh topic — new AIRE session, no prior
    turn history, replayed history folded anew. Idempotent: a channel with no
    topic rows returns `existed=false` and does not raise.

    The recovery need predates the AIRE route (2026-05-19, F+C smoke test: a
    failed `publish_html_artifact` call convinced the agent the tool did not
    exist for as long as its session lived) and covers every persona in the
    channel (2026-07-14: a reset that missed the siblings left a stuck Vultur
    session poisoned in silence).

    `durable=false` in the response means Postgres was unreachable: the reset
    held only in this process's RAM mirrors and a restart loses it — reported,
    never silently equated with a durable one.
    """
    check_auth(authorization)
    result = await aire_route.reset_channel(channel_id)
    log.info(
        "agent_runner_session_reset",
        channel_id=channel_id,
        existed=bool(result["casitas"]),
        casitas=result["casitas"],
        durable=result["durable"],
    )
    return {
        "channel_id": channel_id,
        "existed": bool(result["casitas"]),
        "casitas": result["casitas"],
        "durable": result["durable"],
    }
