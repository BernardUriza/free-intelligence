"""Shared plumbing for the persona_memory MCP tools — PG access + result envelopes.

Two access shapes, on purpose, because the two callers pay very different costs:

- ``_connect()`` — the original one-shot connection (architecture mirrors
  `pg_state.py`). The MCP tools keep it: the agent invokes them RARELY, only
  when the model chooses to reach for memory, so a connection per call is a
  fair price for zero coupling to the runner's event-loop lifecycle.
- ``acquire()`` — a lazily-built shared pool, for callers on the TURN hot path.
  The AIRE route pre-fetches the author's facts in-band on EVERY turn whether
  the model asked for memory or not, so a connect + TLS handshake + close to
  Azure Postgres per turn is latency nobody chose to spend. The pool lives HERE
  and not in the route (Art. 6: one home for the connection policy), so any
  future hot-path caller reuses it instead of minting its own.

Both return ``None`` when Postgres is unreachable — a memory-less turn beats a
dead one, and a DB fault never kills a turn (repo law).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import structlog

log = structlog.get_logger()

_POOL_MIN_SIZE = int(os.environ.get("PG_POOL_MIN_SIZE", "1"))
_POOL_MAX_SIZE = int(os.environ.get("PG_POOL_MAX_SIZE", "4"))

_pool: asyncpg.Pool | None = None
# Lazy-initialized inside the running loop, exactly like api/judge.py's
# semaphore: a module-level asyncio.Lock can bind to the wrong/closed loop under
# some test + uvicorn-reload setups.
_pool_lock: asyncio.Lock | None = None


async def _connect() -> asyncpg.Connection | None:
    """One-shot Postgres connection. Returns None when PG is unreachable."""
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        return await asyncpg.connect(url)
    except Exception:
        log.exception("mcp_tools_pg_connect_failed")
        return None


def _get_pool_lock() -> asyncio.Lock:
    """The pool-creation gate, built on first use inside the active loop."""
    global _pool_lock
    if _pool_lock is None:
        _pool_lock = asyncio.Lock()
    return _pool_lock


async def get_pool() -> asyncpg.Pool | None:
    """The process-wide asyncpg pool, created on first use. None when PG is
    unreachable or unconfigured — never an exception, never a retry storm."""
    global _pool
    if _pool is not None:
        return _pool
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    async with _get_pool_lock():
        if _pool is None:
            try:
                _pool = await asyncpg.create_pool(url, min_size=_POOL_MIN_SIZE, max_size=_POOL_MAX_SIZE)
            except Exception:
                log.exception("mcp_tools_pg_pool_failed")
                return None
    return _pool


@asynccontextmanager
async def acquire() -> AsyncIterator[asyncpg.Connection | None]:
    """Yield a POOLED connection for the duration of the block, or ``None`` when
    Postgres is unreachable. The connection is always released back, never
    closed — closing a pooled connection is what turns a pool back into a
    connect-per-call."""
    pool = await get_pool()
    if pool is None:
        yield None
        return
    try:
        conn = await pool.acquire()
    except Exception:
        log.exception("mcp_tools_pg_acquire_failed")
        yield None
        return
    try:
        yield conn
    finally:
        with contextlib.suppress(Exception):
            await pool.release(conn)


async def close_pool() -> None:
    """Close the shared pool on shutdown. Idempotent; safe when none was built."""
    global _pool, _pool_lock
    pool, _pool, _pool_lock = _pool, None, None
    if pool is None:
        return
    try:
        await pool.close()
    except Exception:
        log.exception("mcp_tools_pg_pool_close_failed")


def _text(payload: str) -> dict:
    """Wrap a string into the MCP tool-result content envelope."""
    return {"content": [{"type": "text", "text": payload}]}


def _error(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}
