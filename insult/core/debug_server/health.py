"""Liveness/readiness endpoint + Postgres probe.

``/debug/health`` is the only unauthenticated endpoint (Azure Container Apps
probe + synthetic-monitor KQL alert). Always 200; the body carries the real
signals so a transient PG blip never restarts a healthy bot.
"""

from __future__ import annotations

from aiohttp import web

from insult.core.debug_server.keys import _MEMORY_KEY
from insult.core.health_state import get_state as get_health_state
from insult.core.memory import MemoryStore


async def _handle_health(request: web.Request) -> web.Response:
    """Liveness + readiness + bot-responsive triplet for Azure Container
    Apps health probes and the synthetic-monitor KQL alert.

    Distinguishes failure modes that previously collapsed into "alive":
    - ``status=ok`` alone = process up, event loop ticking.
    - ``is_ready=true`` = Discord gateway connected.
    - ``last_turn_within_15min=true`` = ``on_message`` actually
      processed something recently (catches the zombie-handler case
      that produced the 2026-05-08T23:59 outage).
    - ``pg.reachable`` (v3.8.7) = Postgres pool can answer SELECT 1
      within 1s. Catches the case where the bot is alive at the gateway
      but the data plane is gone — turns would hang at
      ``stage_memory_stored`` and look like processing latency rather
      than a hard failure.

    Always 200 — the synthetic monitor is responsible for interpreting
    the body. A non-200 here would conflate "probe failed" with "PG had
    a hiccup", and Azure Container Apps would needlessly restart a
    healthy bot during transient DB blips. The PG signal is reported as
    metadata for KQL alerts to act on, not as a liveness gate.
    """
    state = get_health_state()
    pg_status = await _pg_health(request.app[_MEMORY_KEY])
    return web.json_response(
        {
            "status": "ok",
            "is_ready": state.is_bot_ready(),
            "gateway_latency_ms": state.gateway_latency_ms(),
            "last_turn_age_s": state.last_turn_age_s(),
            "last_turn_within_15min": state.last_turn_within(15 * 60),
            "last_turn_outcome": state.last_turn_outcome(),
            "uptime_s": round(state.uptime_s(), 1),
            "turns_total": state.turns_total(),
            "pg": pg_status,
        }
    )


async def _pg_health(memory: MemoryStore) -> dict:
    """Probe the Postgres pool with a 1s-timeout SELECT 1.

    Reports ``{reachable, latency_ms, error}``. We swallow every exception
    so a transient PG failure CANNOT make /debug/health 500 — Azure liveness
    must stay flat (see docstring rationale).

    Lives in this module rather than memory/connection.py because it's a
    health-probe concern: keeping it close to the endpoint that consumes it
    means future tweaks (adding pool stats, slow-query gauge) stay one-file.
    """
    import asyncio as _asyncio
    import time as _time

    pool = getattr(memory, "_manager", None)
    pool = pool.pool if pool is not None else None
    if pool is None:
        return {"reachable": False, "latency_ms": None, "error": "pool_not_initialized"}

    start = _time.monotonic()
    try:
        async with _asyncio.timeout(1.0):
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        return {
            "reachable": True,
            "latency_ms": int((_time.monotonic() - start) * 1000),
            "error": None,
        }
    except TimeoutError:
        return {"reachable": False, "latency_ms": None, "error": "timeout_1s"}
    except Exception as e:
        # Anything else — connection refused, auth error, server gone —
        # surface the class name + one short reason. Don't leak the DSN
        # or any auth payload.
        return {
            "reachable": False,
            "latency_ms": None,
            "error": f"{type(e).__name__}: {str(e).splitlines()[0][:120]}",
        }
