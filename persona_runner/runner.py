"""FastAPI service hosting the Claude Agent SDK loop for every Khimeras persona.

This module is the ORCHESTRATOR only: boot checks, the session reaper's lifecycle,
and mounting the API routers. It was a 1,076-line monolith until 2026-07-14, when
config, schemas, auth, persona loading, turn framing, option building, the session
pool and four endpoint groups each got their own home:

    core/     config.py · schemas.py · auth.py        (env, wire contracts, bearer)
    engine/   persona_files.py · framing.py           (persona DNA, turn assembly)
              options.py · session_pool.py            (SDK options, the LRU pool)
    routing/  model_routing.py · router_runtime.py    (3-tier model choice)
    api/      turn.py · judge.py · workspace.py · ops.py

Entrypoint contract is UNCHANGED — `uvicorn persona_runner.runner:app` (see
infra/azure/entrypoint.sh), so the container never noticed the surgery.

Auth model: OAuth Max only. The credentials.json is written to
`/home/runner/.claude/.credentials.json` by the entrypoint script. No API key
fallback.
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from persona_runner.api import artifacts, judge, ops, turn, workspace
from persona_runner.core import config
from persona_runner.engine import session_pool
from persona_runner.engine.options import REQUIRED_BUILTIN_TOOLS, build_options
from shared.logging_setup import configure_structlog

log = structlog.get_logger()

_reaper_task: asyncio.Task | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Verify workspace + capabilities at boot, spawn the idle-session reaper,
    tear every client down on shutdown."""
    global _reaper_task
    configure_structlog()
    if not config.WORKSPACE_ROOT.exists():
        log.error("agent_runner_workspace_missing", path=str(config.WORKSPACE_ROOT))
    if not config.RUNNER_AUTH_TOKEN:
        log.warning("agent_runner_no_auth_token_configured")
    log.info(
        "agent_runner_starting",
        workspace=str(config.WORKSPACE_ROOT),
        persona=str(config.PERSONA_PATH),
        model=config.DEFAULT_MODEL,
        token_set=bool(config.RUNNER_AUTH_TOKEN),
        session_idle_timeout_s=config.SESSION_IDLE_TIMEOUT_S,
    )
    # Capability self-check: a runner that boots "healthy" but cannot web-search is
    # a fake-green. Build options once and let verify_required_tools crash startup
    # LOUDLY if WebSearch is missing — the container fails to come up instead of
    # silently deflecting every factual question (2026-06-14).
    await build_options("__boot_capability_check__")
    log.info("agent_runner_capabilities_ok", required=list(REQUIRED_BUILTIN_TOOLS))

    _reaper_task = asyncio.create_task(session_pool.reap_idle_sessions(), name="session_reaper")
    yield

    if _reaper_task is not None:
        _reaper_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _reaper_task
    await session_pool.close_all()
    log.info("agent_runner_stopped")


app = FastAPI(title="Khimeras Persona Runner", version="1.0.0", lifespan=_lifespan)

app.include_router(ops.router)
app.include_router(turn.router)
app.include_router(judge.router)
app.include_router(workspace.router)
app.include_router(artifacts.router)
