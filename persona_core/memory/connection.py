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
- Schema lives in `persona_core/memory/postgres_schema.sql` and is
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

import asyncio
import time
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
        self._prewarm_task: asyncio.Task | None = None

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

        Every boundary here emits a structured log (`pg_pool_creating` →
        `pg_pool_created` → `pg_schema_applying` → `pg_schema_applied` →
        `memory_connected_pg`) so a boot that stalls inside any step is
        diagnosable from telemetry alone — no blind spot. This exists because
        on 2026-06-13 a boot deadlocked somewhere in here with ZERO logs
        between `debug_server_started` and the success line, making the root
        cause unprovable. Never let a critical span go dark again.
        """
        # Idempotent across gateway reconnects: on_ready can fire more than
        # once, and rebuilding the pool would orphan the previous one (a
        # connection leak) and needlessly re-run the schema. The pool persists.
        if self._pool is not None:
            log.info("pg_connect_skipped_already_connected", pool_size=self._max_size)
            return

        log.info("pg_pool_creating", min_size=self._min_size, max_size=self._max_size)
        self._pool = await asyncpg.create_pool(
            dsn=self._postgres_url,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=30,
            init=self._init_connection,
        )
        log.info("pg_pool_created", min_size=self._min_size, max_size=self._max_size)

        # Run schema. Safe on existing DBs (everything IF NOT EXISTS).
        if _SCHEMA_PATH.exists():
            schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
            log.info("pg_schema_applying")
            async with self._pool.acquire() as conn:
                await conn.execute(schema_sql)
            log.info("pg_schema_applied")

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

        # Pre-warm the embedding model OFF the critical boot path. The warmup
        # forces sentence-transformers to download `all-MiniLM-L6-v2` from
        # HuggingFace on a fresh container — a slow, network-dependent step that
        # MUST NOT gate `bot_ready`. Fire-and-forget: the first turn falls back
        # to the lazy load if the warmup hasn't finished. (Previously this was
        # `await`-ed inside connect(), so a slow/hung HF download blocked the
        # whole bot from becoming ready — a boot stall vector.)
        if self._vectors_available:
            self._prewarm_task = asyncio.create_task(self._prewarm_embeddings())

    async def _prewarm_embeddings(self) -> None:
        """Warm the embedding model in the background. Runs in a thread because
        the encode is sync CPU work; never blocks the event loop heartbeat.
        Non-fatal — failure just means the first turn pays the lazy-load cost."""
        from persona_core.vectors import get_embedding_model

        warmup_start = time.monotonic()
        log.info("embedding_prewarm_start")
        try:
            await asyncio.to_thread(lambda: get_embedding_model().embed("boot warmup"))
            log.info("embedding_model_prewarmed", elapsed_ms=int((time.monotonic() - warmup_start) * 1000))
        except Exception as e:
            log.warning("embedding_prewarm_failed", error=str(e))

    async def _init_connection(self, conn: asyncpg.Connection) -> None:
        """Per-connection setup. Runs once when a connection joins the
        pool. Registers the pgvector codec if available so VECTOR(N)
        columns are usable as Python sequences without manual encoding.
        """
        try:
            from pgvector.asyncpg import register_vector

            await register_vector(conn)
        except Exception as e:
            # pgvector codec not available — semantic-search code paths
            # will degrade to "vectors_available=False" and skip.
            log.debug("pgvector_codec_skipped", reason=str(e))

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
