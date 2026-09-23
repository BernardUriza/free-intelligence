"""FastAPI service fronting AIRE's engine door for every Khimeras persona.

This module is the ORCHESTRATOR only: boot checks and mounting the API routers.
It was a 1,076-line monolith until 2026-07-14, when config, schemas, auth,
persona loading, turn framing and the endpoint groups each got their own home:

    core/     config.py · schemas.py · auth.py        (env, wire contracts, bearer)
    engine/   persona_files.py · framing.py           (persona DNA, turn assembly)
              aire_route.py · aire_topic.py           (the AIRE door, the topic axis)
    routing/  model_routing.py · router_runtime.py    (3-tier model choice)
    api/      turn.py · judge.py · workspace.py · ops.py · mcp_http.py

It hosted the Claude Agent SDK in-process (session pool, idle reaper, option
building) until the AIRE flag flipped permanent — backlog
``aire-engine-stage2.md``, deletion step. Turns now ride
``POST /projects/{p}/sessions/{s}/messages`` against AIRE's engine door; the
Anthropic credential lives on the droplet, never in this container.

Entrypoint contract is UNCHANGED — `uvicorn persona_runner.runner:app` (see
infra/azure/entrypoint.sh), so the container never noticed the surgery.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from persona_runner.api import artifacts, judge, mcp_http, ops, turn, workspace
from persona_runner.core import config
from shared.logging_setup import configure_structlog

log = structlog.get_logger()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Verify the AIRE route at boot; close the door clients and the PG pool on
    shutdown."""
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
    )
    # Capability self-check: a runner that boots "healthy" but cannot web-search
    # is a fake-green. Assert the route that will ACTUALLY serve turns and crash
    # startup LOUDLY when it is wrong — the container fails to come up instead of
    # silently deflecting every factual question (2026-06-14).
    from persona_runner.engine import aire_route, turn_jobs

    aire_route.verify_aire_route()
    log.info(
        "agent_runner_capabilities_ok",
        backend="aire",
        required=list(aire_route.AIRE_REQUIRED_TOOLS),
        mode=config.AIRE_TURN_MODE,
    )
    # Boletos durables: el latido mantiene vivas nuestras filas, y la réplica
    # anterior pudo dejar jobs huérfanos que se reanudan en background — nunca
    # bloquea el boot, un ledger caído sólo lo loggea.
    turn_jobs.JOBS.start_heartbeat()
    boot_resume = asyncio.create_task(turn_jobs.resume_stale_at_boot(aire_route.turn_via_aire))

    yield

    # Drenar ANTES de cerrar los clientes de AIRE y el pool: los jobs abiertos
    # los usan. Al vencer la espera, sus filas se sueltan para la sucesora.
    boot_resume.cancel()
    await turn_jobs.drain_for_shutdown(config.RUNNER_SHUTDOWN_DRAIN_S)
    await turn_jobs.JOBS.stop_heartbeat()
    # Every AIREBackend holds a pooled httpx.AsyncClient — turn backends and
    # judge backends alike get their connections and TLS sessions closed.
    await aire_route.close_backends()
    # The shared asyncpg pool (mcp_tools.shared) is built lazily by whoever
    # needs Postgres on the hot path; closing is idempotent when none exists.
    from persona_runner.mcp_tools import shared as pg_shared

    await pg_shared.close_pool()
    log.info("agent_runner_stopped")


app = FastAPI(
    title="Khimeras Persona Runner",
    version="1.0.0",
    lifespan=_lifespan,
    # See config.DOCS_ENABLED: this is the only app with external ingress, so the
    # default-on interactive docs were serving the API map to the open internet.
    docs_url="/docs" if config.DOCS_ENABLED else None,
    redoc_url="/redoc" if config.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if config.DOCS_ENABLED else None,
)

app.include_router(ops.router)
app.include_router(turn.router)
app.include_router(judge.router)
app.include_router(workspace.router)
app.include_router(artifacts.router)
app.include_router(mcp_http.router)
