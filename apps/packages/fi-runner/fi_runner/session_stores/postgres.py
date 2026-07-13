"""Postgres-backed :class:`~claude_agent_sdk.SessionStore`.

PROVENANCE — this is Anthropic's OFFICIAL reference adapter, copied, not written:

    anthropics/claude-agent-sdk-python
    examples/session_stores/postgres_session_store.py

Its own docstring says "copy it into your project and adapt as needed", which is
exactly what this is. Writing a Postgres store by hand would be reinventing code
that already ships — the very failure this wiring exists to repair.

Two adaptations, both deliberate and marked ADAPTED below:

1. ``append()`` DEDUPLICATES by ``entry["uuid"]``. The SDK may re-send entries
   (a retried flush, a reconnect), and the upstream adapter would happily insert
   the same transcript entry twice — ``seq`` is a bigserial, so nothing stops it.
   A duplicated ``tool_result`` in a resumed transcript is not cosmetic.
2. A ``create_postgres_session_store()`` factory that imports asyncpg LAZILY, so
   fi-runner never pulls a database driver at import time. The driver lives
   behind the optional ``[postgres]`` extra.

Requires ``asyncpg`` (the native asyncio Postgres driver). Install with::

    pip install asyncpg

Usage::

    import asyncpg
    from claude_agent_sdk import ClaudeAgentOptions, query

    from postgres_session_store import PostgresSessionStore

    pool = await asyncpg.create_pool("postgresql://...")
    store = PostgresSessionStore(pool=pool)
    await store.create_schema()  # one-time, idempotent

    async for message in query(
        prompt="Hello!",
        options=ClaudeAgentOptions(session_store=store),
    ):
        ...  # messages are mirrored to Postgres as they stream

Schema (one row per transcript entry; ``seq`` orders entries within a key)::

    CREATE TABLE IF NOT EXISTS claude_session_store (
      project_key text   NOT NULL,
      session_id  text   NOT NULL,
      subpath     text   NOT NULL DEFAULT '',
      seq         bigserial,
      entry       jsonb  NOT NULL,
      mtime       bigint NOT NULL,
      PRIMARY KEY (project_key, session_id, subpath, seq)
    );
    CREATE INDEX IF NOT EXISTS claude_session_store_list_idx
      ON claude_session_store (project_key, session_id) WHERE subpath = '';

The empty string is the ``subpath`` sentinel for the main transcript so the
composite primary key is total (Postgres treats ``NULL`` as distinct in PKs).

JSONB key ordering
------------------
Entries are stored as ``jsonb``, which **reorders object keys** on read-back
(shorter keys first, then by byte order — see the Postgres docs). This is
explicitly allowed by the :class:`~claude_agent_sdk.SessionStore` contract:
:meth:`~claude_agent_sdk.SessionStore.load` requires *deep-equal*, not
*byte-equal*, returns. The SDK never hashes or byte-compares stored entries,
and the ``*_from_store`` read helpers hoist ``"type"`` to the first key when
re-serializing so the SDK's lite-parse tag scan still works. If you need
byte-stable storage, switch the column to ``json`` (preserves text as-is) or
``text`` and ``json.dumps`` yourself.

Retention: this adapter never deletes rows on its own. Add a scheduled
``DELETE ... WHERE mtime < $cutoff`` (or table partitioning by ``mtime``) to
expire transcripts according to your compliance requirements. Local-disk
transcripts under ``CLAUDE_CONFIG_DIR`` are swept independently by the CLI's
``cleanupPeriodDays`` setting.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from claude_agent_sdk import (
    SessionKey,
    SessionListSubkeysKey,
    SessionStore,
    SessionStoreEntry,
    SessionStoreListEntry,
)

if TYPE_CHECKING:
    import asyncpg

#: Conservative identifier guard for the table name. The name is interpolated
#: into DDL/DML (asyncpg cannot parameterize identifiers), so reject anything
#: that isn't a plain ``[A-Za-z_][A-Za-z0-9_]*`` to rule out injection.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass
class PostgresSessionStoreOptions:
    """Configuration for :class:`PostgresSessionStore`."""

    pool: asyncpg.Pool
    """Pre-configured ``asyncpg.Pool``. Caller controls DSN, auth, TLS,
    pool sizing, etc. A pool (not a single connection) is required so the
    adapter can be shared across concurrent batcher flushes."""

    table: str = "claude_session_store"
    """Table name. Must match ``[A-Za-z_][A-Za-z0-9_]*`` — it is interpolated
    directly into SQL (identifiers cannot be parameterized)."""


class PostgresSessionStore(SessionStore):
    """Postgres-backed :class:`~claude_agent_sdk.SessionStore`.

    One row per transcript entry. ``append()`` is a single multi-row
    ``INSERT``; ``load()`` is ``SELECT entry ... ORDER BY seq``.

    Args:
        pool: Pre-configured ``asyncpg.Pool``.
        table: Table name (default ``"claude_session_store"``). Must be a
            plain identifier — validated against ``[A-Za-z_][A-Za-z0-9_]*``.
        options: Alternative to positional args; takes precedence if given.
    """

    def __init__(
        self,
        pool: asyncpg.Pool | None = None,
        table: str = "claude_session_store",
        *,
        options: PostgresSessionStoreOptions | None = None,
    ) -> None:
        if options is not None:
            pool = options.pool
            table = options.table
        if pool is None:
            raise ValueError("PostgresSessionStore requires 'pool'")
        if not _IDENT_RE.match(table):
            raise ValueError(
                f"table {table!r} must match [A-Za-z_][A-Za-z0-9_]* "
                "(it is interpolated into SQL)"
            )
        self._pool = pool
        self._table = table

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    async def create_schema(self) -> None:
        """Create the table and listing index if absent. Idempotent.

        Call once at startup (or run the equivalent migration out-of-band).
        The partial index on ``subpath = ''`` keeps :meth:`list_sessions`
        cheap without indexing every subagent row.
        """
        # f-string interpolation of self._table is safe: validated against
        # _IDENT_RE in __init__.
        await self._pool.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self._table} (
              project_key text   NOT NULL,
              session_id  text   NOT NULL,
              subpath     text   NOT NULL DEFAULT '',
              seq         bigserial,
              entry       jsonb  NOT NULL,
              mtime       bigint NOT NULL,
              -- ADAPTED: the entry's own uuid, lifted out of the jsonb so it can
              -- be indexed. Generated (never written by hand) so it cannot drift
              -- from the entry it identifies.
              entry_uuid  text GENERATED ALWAYS AS (entry->>'uuid') STORED,
              PRIMARY KEY (project_key, session_id, subpath, seq)
            );
            CREATE INDEX IF NOT EXISTS {self._table}_list_idx
              ON {self._table} (project_key, session_id) WHERE subpath = '';
            -- ADAPTED: what makes append() idempotent. PARTIAL, so an entry with
            -- no uuid is simply not deduplicated (it appends, as upstream does)
            -- instead of colliding with every other uuid-less entry on NULL.
            CREATE UNIQUE INDEX IF NOT EXISTS {self._table}_uuid_idx
              ON {self._table} (project_key, session_id, subpath, entry_uuid)
              WHERE entry_uuid IS NOT NULL;
            """
        )

    # ------------------------------------------------------------------
    # SessionStore protocol
    # ------------------------------------------------------------------

    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]) -> None:
        if not entries:
            return
        subpath = key.get("subpath") or ""
        # Single round-trip multi-row INSERT: unnest() the jsonb[] payload so
        # the whole batch lands in one statement (atomic, ordered by array
        # position via WITH ORDINALITY, one bigserial draw per row).
        #
        # ADAPTED — ON CONFLICT DO NOTHING against the uuid index. The SDK may
        # re-send an entry it already flushed (a retry, a reconnect); upstream
        # this inserted it twice, because `seq` is a bigserial and nothing
        # deduplicates. A transcript that replays the same tool_result twice is
        # a corrupted memory, not a cosmetic wart. Entries WITHOUT a uuid are
        # never deduplicated (the partial index does not cover them) — they
        # append as before.
        await self._pool.execute(
            f"""
            INSERT INTO {self._table} (project_key, session_id, subpath, entry, mtime)
            SELECT $1, $2, $3, e,
                   (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::bigint
            FROM unnest($4::jsonb[]) WITH ORDINALITY AS t(e, ord)
            ORDER BY ord
            ON CONFLICT (project_key, session_id, subpath, entry_uuid)
              WHERE entry_uuid IS NOT NULL
              DO NOTHING
            """,
            key["project_key"],
            key["session_id"],
            subpath,
            [json.dumps(e) for e in entries],
        )

    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        rows = await self._pool.fetch(
            f"""
            SELECT entry FROM {self._table}
            WHERE project_key = $1 AND session_id = $2 AND subpath = $3
            ORDER BY seq
            """,
            key["project_key"],
            key["session_id"],
            key.get("subpath") or "",
        )
        if not rows:
            return None
        # asyncpg returns jsonb as the raw JSON text by default (no codec
        # registered on the pool); decode each row. If a jsonb codec IS
        # registered, the value is already a dict — pass it through.
        out: list[SessionStoreEntry] = []
        for row in rows:
            v = row["entry"]
            out.append(json.loads(v) if isinstance(v, (str, bytes)) else v)
        return out

    async def list_sessions(self, project_key: str) -> list[SessionStoreListEntry]:
        rows = await self._pool.fetch(
            f"""
            SELECT session_id, MAX(mtime) AS mtime FROM {self._table}
            WHERE project_key = $1 AND subpath = ''
            GROUP BY session_id
            """,
            project_key,
        )
        return [{"session_id": r["session_id"], "mtime": int(r["mtime"])} for r in rows]

    async def delete(self, key: SessionKey) -> None:
        subpath = key.get("subpath")
        if subpath:
            # Targeted: remove just this subpath's rows.
            await self._pool.execute(
                f"""
                DELETE FROM {self._table}
                WHERE project_key = $1 AND session_id = $2 AND subpath = $3
                """,
                key["project_key"],
                key["session_id"],
                subpath,
            )
            return
        # Cascade: main + every subpath under this (project_key, session_id).
        await self._pool.execute(
            f"""
            DELETE FROM {self._table}
            WHERE project_key = $1 AND session_id = $2
            """,
            key["project_key"],
            key["session_id"],
        )

    async def list_subkeys(self, key: SessionListSubkeysKey) -> list[str]:
        rows = await self._pool.fetch(
            f"""
            SELECT DISTINCT subpath FROM {self._table}
            WHERE project_key = $1 AND session_id = $2 AND subpath <> ''
            """,
            key["project_key"],
            key["session_id"],
        )
        return [r["subpath"] for r in rows]


async def create_postgres_session_store(
    dsn: str,
    *,
    table: str = "claude_session_store",
    create_schema: bool = True,
    **pool_kwargs: object,
) -> PostgresSessionStore:
    """Build a store from a DSN — the convenience path for a deploy that has no
    pool of its own yet.

    ADAPTED (not upstream). asyncpg is imported HERE, inside the call, never at
    module import: fi-runner must not drag a database driver into every process
    that merely imports it. The driver lives behind the optional extra, and the
    error says so instead of surfacing a bare ModuleNotFoundError.

    A deploy that already owns a pool should skip this and construct
    ``PostgresSessionStore(pool=...)`` directly — the port takes the store, and
    fi-runner neither owns the DSN nor the credentials.
    """
    try:
        import asyncpg
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            "PostgresSessionStore requires asyncpg. "
            "Install via: pip install 'fi-runner[postgres]'"
        ) from exc

    pool = await asyncpg.create_pool(dsn, **pool_kwargs)  # type: ignore[arg-type]
    store = PostgresSessionStore(pool=pool, table=table)
    if create_schema:
        await store.create_schema()
    return store
