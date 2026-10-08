"""The transcript of an ACP turn, appended to the owner's Postgres — because no
ACP agent has a `session_store`. Claude's SDK mirrors its own JSONL through the
store adapter; every other agent (Codex, Gemini, Qwen, Kimi, …) writes its
memory to the box's mortal disk in its own format, which by the litmus test in
CLAUDE.md gives the agent a body back. So for ACP the daemon holds the pen
itself: every `session/update`, every prompt and every stop reason lands here,
eagerly, as it happens ([[log-is-the-truth]]).

The table also carries the ONE mapping the native path never needed: AIRE names
a session by `uuid5`, but an ACP agent mints its own id on `session/new`, so
`agent_session` remembers which agent session answers to which AIRE session —
the read that lets the next turn `session/load` instead of forgetting. It feeds
the machine's resume decision, never a human's eyes ([[write-only-daemon]]).
Created as role `aire`, so the reader's default grant covers it."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from . import db

TABLE = "aire_agent_log"
TIMEOUT_S = float(os.environ.get("AIRE_ACP_MIRROR_TIMEOUT_S", "5"))
STATEMENT_TIMEOUT_MS = int(TIMEOUT_S * 1000)

DDL = (
    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
    " seq bigserial PRIMARY KEY,"
    " at timestamptz NOT NULL DEFAULT now(),"
    " project_key text NOT NULL,"
    " session_id text NOT NULL,"
    " provider text NOT NULL,"
    " agent_session text,"
    " kind text NOT NULL,"
    " entry jsonb NOT NULL)"
)
INDEX = (f"CREATE INDEX IF NOT EXISTS {TABLE}_session ON {TABLE}"
         " (project_key, session_id, provider, seq)")

_ready = False
_lock = asyncio.Lock()


async def ensure() -> None:
    """The DDL on its OWN autocommit connection, `_ready` flipped only once it
    is committed — the lesson `spend.ensure` paid for."""
    global _ready
    if _ready or not db.dsn():
        return
    async with _lock:
        if _ready:
            return
        async with db.acquire() as conn:
            await conn.execute(DDL)
            await conn.execute(INDEX)
        _ready = True


async def append(project_key: str, session_id: str, provider: str,
                 agent_session: str | None, kind: str, entry: dict[str, Any]) -> None:
    """One transcript entry, appended. Never raises into a turn — the agent's
    answer is already streaming and a dead database must not eat it — but LOUD,
    because for ACP this row IS the memory: a turn that left no row is lost."""
    if not db.dsn():
        return
    try:
        await asyncio.wait_for(
            _insert(project_key, session_id, provider, agent_session, kind, entry),
            timeout=TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — the mirror never kills a turn
        print(f"ACP-MIRROR-LOST {provider} {project_key}/{session_id} {kind}: "
              f"{type(exc).__name__}: {exc}", flush=True)


async def _insert(project_key: str, session_id: str, provider: str,
                  agent_session: str | None, kind: str, entry: dict[str, Any]) -> None:
    await ensure()
    async with db.acquire(STATEMENT_TIMEOUT_MS) as conn:
        await conn.execute(
            f"INSERT INTO {TABLE} (project_key, session_id, provider, agent_session, kind, entry)"
            " VALUES ($1, $2, $3, $4, $5, $6::jsonb)",
            project_key, session_id, provider, agent_session, kind,
            json.dumps(entry, ensure_ascii=False, default=str))


async def agent_session(project_key: str, session_id: str, provider: str) -> str | None:
    """The agent-side id the latest `session` row bound to this AIRE session,
    or None when this provider has never served it. RAISES on a dead database:
    a lookup that quietly returned None would fork the memory into a fresh
    agent session, and a silent fork is worse than a failed turn."""
    if not db.dsn():
        return None
    await ensure()
    async with db.acquire(STATEMENT_TIMEOUT_MS) as conn:
        return await conn.fetchval(
            f"SELECT agent_session FROM {TABLE}"
            " WHERE project_key = $1 AND session_id = $2 AND provider = $3 AND kind = 'session'"
            " ORDER BY seq DESC LIMIT 1",
            project_key, session_id, provider)
