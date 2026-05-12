"""Owns the asyncpg pool, schema verification, and pgvector init.

Post-PG migration (2026-05-12): the bot's memory store moved from
SQLite-in-blob-storage to Azure Database for PostgreSQL Flexible Server.
The container is now stateless from a data perspective — deploys cannot
mutate the DB, rolling updates work natively, cero race condition.

Architecture:
- `asyncpg.Pool` shared across all repositories (each calls
  `pool.execute/fetch/...` via `BaseRepository` helpers).
- Connection string supplied via `POSTGRES_URL` env var (Pydantic
  Settings reads it). Format:
  `postgresql://user:pass@host:5432/dbname?sslmode=require`
- Schema lives in `insult/core/memory/postgres_schema.sql` and is
  applied once at startup (idempotent — `CREATE TABLE IF NOT EXISTS`).
- pgvector enabled at the Azure server level (azure.extensions=VECTOR);
  this module verifies it loaded with `CREATE EXTENSION IF NOT EXISTS vector`.

Lifecycle:
- `connect()` builds the pool, runs the schema file, registers
  pgvector codec. Idempotent.
- `close()` drains and closes the pool.
- `get_connection()` / `pool` exposed for repositories.

Why a pool and not a single connection:
- Postgres handles concurrency natively (MVCC). We can issue concurrent
  reads/writes from different repos without WAL contention.
- Pool of 5 connections matches the typical concurrent stages: facts
  load + recent messages + disclosure scan + Other People facts +
  preset_classifier_llm pre-roll. The previous SQLite single-writer
  bottleneck disappears.
"""

from __future__ import annotations

from pathlib import Path

import asyncpg
import structlog

log = structlog.get_logger()

# Schema lives next to this file. Loaded once at connect() and
# re-applied idempotently on each boot (CREATE TABLE IF NOT EXISTS).
_SCHEMA_PATH = Path(__file__).parent / "postgres_schema.sql"


class ConnectionManager:
    """Lifecycle manager for the shared asyncpg pool.

    Construction takes a `postgres_url` (full DSN). `connect()` builds
    the pool and applies the schema. `pool` is the live `asyncpg.Pool`
    that `BaseRepository._pool` returns to repository helpers.
    """

    def __init__(self, postgres_url: str, *, min_size: int = 2, max_size: int = 10):
        self._postgres_url = postgres_url
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None
        self._vectors_available: bool = False

    @property
    def pool(self) -> asyncpg.Pool | None:
        """The live pool, or None if connect() hasn't been called yet."""
        return self._pool

    @property
    def vectors_available(self) -> bool:
        """Whether pgvector loaded successfully. Repositories that do
        semantic search check this before calling vector ops."""
        return self._vectors_available

    async def connect(self) -> None:
        """Build the pool, apply the schema, register pgvector codec.

        Idempotent: safe to call on boot of an existing database. The
        schema file uses `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX
        IF NOT EXISTS` everywhere so re-running does nothing harmful.

        pgvector codec is registered per-connection via `init=` callback
        so every connection acquired from the pool can pass Python
        sequences as `VECTOR(N)` parameters and receive them as
        `numpy.ndarray` / list-of-floats.
        """
        self._pool = await asyncpg.create_pool(
            dsn=self._postgres_url,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=30,
            init=self._init_connection,
        )

        # Run schema. Safe on existing DBs (everything IF NOT EXISTS).
        if _SCHEMA_PATH.exists():
            schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
            async with self._pool.acquire() as conn:
                await conn.execute(schema_sql)

        # Confirm pgvector is queryable — best-effort flag for repos
        # that need semantic search.
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            self._vectors_available = True
            log.info("memory_connected_pg", vectors=True, pool_size=self._max_size)
        except Exception as e:
            self._vectors_available = False
            log.warning("memory_connected_pg_no_vectors", reason=str(e))

    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        """Per-connection setup. Runs once when a connection joins the
        pool. Registers the pgvector codec if available so VECTOR(N)
        columns are usable as Python sequences without manual encoding.
        """
        try:
            from pgvector.asyncpg import register_vector

            await register_vector(conn)
        except Exception:
            # pgvector codec not available — semantic-search code paths
            # will degrade to "vectors_available=False" and skip.
            pass

    async def get_connection(self):
        """Compatibility shim for old callers that did
        `await self._conn()` and expected a single connection. New code
        should use the `_pool` directly via BaseRepository helpers.

        Returns an async context manager: `async with cm.get_connection() as c:`
        """
        if self._pool is None:
            raise RuntimeError("ConnectionManager.connect() not called")
        return self._pool.acquire()

    async def close(self) -> None:
        """Drain and close the pool. No WAL checkpoint needed (Postgres
        is fully durable on its own); no blob upload needed (the DB is
        external and persistent across container restarts)."""
        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None
        log.info("memory_closed_pg")
