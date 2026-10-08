"""One way to reach Postgres, for every call site that used to open its own.

Measured on the droplet, against the real database: **185–236 ms to connect,
12–29 ms to run the query**. Five modules paid that toll on every call —
`tokens` on every billed gateway turn, `access` on every invitation, `roster`
every sixty seconds, `memory_tool` inside a paid turn, `sweep` nightly — which
means the daemon spent roughly fifteen times longer opening the door than
walking through it. From the same box, an `acquire()` off a warm pool costs
**0.0–0.6 ms**. The connection was never the work.

The pen keeps its own long-lived connection and the store keeps its own pool:
both are correct already, and neither is a connect-per-call. This module is for
the ones that were.

The pool is per-PROCESS and lazy: the listener builds one, the server builds
another, and a process that never touches Postgres never imports the driver
(the store's rule — a database driver must not ride into every process that
merely imports AIRE). A oneshot like the broom calls `close()` on its way out.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any, AsyncIterator

CONNECT_TIMEOUT_S = int(os.environ.get("AIRE_DB_TIMEOUT", "10"))
POOL_MAX = int(os.environ.get("AIRE_DB_POOL_MAX", "4"))
POOL_IDLE_S = float(os.environ.get("AIRE_DB_POOL_IDLE_S", "300"))

_pool: Any = None
_loop: Any = None
_lock = asyncio.Lock()


def dsn() -> str:
    """The daemon's single name for its database. Empty means file-only mode,
    which several callers treat as a legitimate no-op — so this returns the
    empty string rather than raising, and the caller keeps its own guard."""
    return os.environ.get("AIRE_DATABASE_URL", "")


async def pool() -> Any:
    """The process's pool, built on first use. A pool belongs to the event loop
    that created it, so a different loop (a test, a oneshot re-entered) gets a
    fresh one instead of connections it can never await."""
    global _pool, _loop
    running = asyncio.get_running_loop()
    if _pool is not None and _loop is running:
        return _pool
    async with _lock:
        if _pool is None or _loop is not running:
            import asyncpg

            _pool = await asyncpg.create_pool(
                dsn(), min_size=1, max_size=POOL_MAX, timeout=CONNECT_TIMEOUT_S,
                max_inactive_connection_lifetime=POOL_IDLE_S)
            _loop = running
    return _pool


@contextlib.asynccontextmanager
async def acquire(statement_timeout_ms: int = 0) -> AsyncIterator[Any]:
    """A connection from the pool, released on the way out even if the body
    raises — the shape the five call sites hand-rolled with try/finally.

    `statement_timeout_ms` is set with SET LOCAL inside a transaction, never on
    the pool: a bound that belongs to ONE query must not follow the connection
    back into the pool and silently govern the next caller's."""
    conn_pool = await pool()
    async with conn_pool.acquire() as conn:
        if not statement_timeout_ms:
            yield conn
            return
        async with conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}")
            yield conn


async def close() -> None:
    """For a process that ENDS — the broom, a test. A long-lived daemon never
    calls this: its pool dies with it.

    A pool can only be closed from the loop that opened it; asking a dead loop
    to abort its sockets raises where the caller is doing the tidy thing. So a
    foreign loop drops the reference instead — those sockets went when their
    loop did."""
    global _pool, _loop
    if _pool is None:
        return
    if _loop is asyncio.get_running_loop():
        await _pool.close()
    _pool, _loop = None, None
