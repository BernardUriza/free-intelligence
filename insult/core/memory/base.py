"""Base class for all memory repositories.

Post-PG migration (2026-05-12) the data plane is Azure Database for
PostgreSQL Flexible Server, accessed via asyncpg. The shared resource
is a `Pool` (no longer a single connection — Postgres handles
concurrency natively), but the repository API stays unchanged from
the caller's perspective:

    rows = await self._fetch("SELECT ... FROM t WHERE id = $1", id)
    row  = await self._fetchrow("SELECT ... WHERE id = $1", id)
    val  = await self._fetchval("SELECT COUNT(*) FROM t")
    await self._execute("INSERT INTO t (a) VALUES ($1)", a)

Differences from the old aiosqlite shape:
- Placeholders: `$1, $2, …` (Postgres), not `?` (SQLite).
- Returns asyncpg `Record` rows — index access (row[0]) works AND
  named access (row['col']) works. Replaces aiosqlite tuple-only rows.
- No explicit commit — asyncpg auto-commits each statement unless
  the caller opens a transaction (use `self._tx()` for that).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import asyncpg

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from insult.core.memory.connection import ConnectionManager


class BaseRepository:
    """Shared superclass for every domain repository.

    Holds the `ConnectionManager` and exposes typed helpers so subclasses
    don't need to know whether the backing store is a single connection
    or a pool. asyncpg pool methods (`execute`, `fetch`, `fetchrow`,
    `fetchval`) are forwarded one-to-one — the pool acquires a connection
    per call and releases it cleanly.
    """

    def __init__(self, manager: ConnectionManager):
        self._manager = manager

    @property
    def _pool(self) -> asyncpg.Pool:
        """Return the live pool. Subclasses use this only when they need
        the pool object directly (transactions, advanced asyncpg features)."""
        pool = self._manager.pool
        if pool is None:
            raise RuntimeError("ConnectionManager is not connected — call connect() first")
        return pool

    async def _execute(self, sql: str, *args: Any) -> str:
        """Run a statement (INSERT/UPDATE/DELETE). Returns the command tag."""
        return await self._pool.execute(sql, *args)

    async def _executemany(self, sql: str, args_seq: list[tuple]) -> None:
        """Run the same statement repeatedly with different args. Faster than
        a Python loop because asyncpg sends a single batched message."""
        await self._pool.executemany(sql, args_seq)

    async def _fetch(self, sql: str, *args: Any) -> list[asyncpg.Record]:
        """Return all rows. Records support both row[0] and row['col']."""
        return await self._pool.fetch(sql, *args)

    async def _fetchrow(self, sql: str, *args: Any) -> asyncpg.Record | None:
        """Return the first row, or None if the query yielded zero rows."""
        return await self._pool.fetchrow(sql, *args)

    async def _fetchval(self, sql: str, *args: Any) -> Any:
        """Return the first column of the first row (or None). Useful for
        COUNT(*), SELECT singletons, and RETURNING-clause id reads."""
        return await self._pool.fetchval(sql, *args)

    @asynccontextmanager
    async def _tx(self) -> AsyncIterator[asyncpg.Connection]:
        """Acquire a connection from the pool and open a transaction.

        Caller does its own statements with the yielded connection. The
        transaction commits on clean exit and rolls back on exception:

            async with self._tx() as conn:
                await conn.execute("INSERT ...")
                await conn.execute("UPDATE ...")
        """
        async with self._pool.acquire() as conn, conn.transaction():
            yield conn

    @property
    def vectors_available(self) -> bool:
        """Whether pgvector initialized successfully at boot."""
        return self._manager.vectors_available
