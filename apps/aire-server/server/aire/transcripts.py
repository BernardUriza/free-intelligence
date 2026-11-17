"""A project's chats, read back as turns — for the agent that works on the project (#55).

The transcript lives in two tables: `claude_session_store` (the Claude SDK's own
store) and `aire_agent_log` (the pen for Codex and every ACP agent). `recall`
already searches both for words; this reads them as conversations — which
sessions a casita has, and what was said in one — so an agent outside the turn
(Claude Code through the projects MCP) can take a project's chats as context.

The read feeds an agent, the `recall` family of [[write-only-daemon]]. It is for
constant tokens only, and any constant token reads any project's chats: no token
is bound to a project (open item). What it returns is the SPOKEN text of the main
thread, flattened IN SQL — tool calls, tool results, attachments, subagent
sidechains (`subpath <> ''`) and usage never leave the database, and only the
last `limit` turns are fetched: a long session must not be loaded whole into a
512 MB droplet to hand back its tail.
"""

from __future__ import annotations

from typing import Any

from . import db
from .agent_sdk import project_key_for_directory
from .engine.core import WORKSPACES
from .keys import sdk_session_uuid

STATEMENT_TIMEOUT_MS = 5_000
MAX_TURNS = 400
_SESSIONS = (
    "SELECT session_id, 'claude' AS provider, count(*) AS entries,"
    " to_timestamp(min(mtime) / CASE WHEN min(mtime) > 1e12 THEN 1000 ELSE 1 END) AS first_at,"
    " to_timestamp(max(mtime) / CASE WHEN max(mtime) > 1e12 THEN 1000 ELSE 1 END) AS last_at"
    " FROM claude_session_store WHERE project_key = $1 AND subpath = '' GROUP BY session_id"
    " UNION ALL"
    " SELECT session_id, min(provider), count(*), min(at), max(at)"
    " FROM aire_agent_log WHERE project_key = $1 GROUP BY session_id"
)
_SDK_CONTENT = "entry->'message'->'content'"
_TURNS = (
    "SELECT * FROM ("
    " SELECT 'claude' AS src, entry->>'type' AS role,"
    f"  CASE jsonb_typeof({_SDK_CONTENT}) WHEN 'string' THEN entry->'message'->>'content'"
    "   WHEN 'array' THEN (SELECT string_agg(b->>'text', E'\\n')"
    f"    FROM jsonb_array_elements({_SDK_CONTENT}) b WHERE b->>'type' = 'text')"
    "   ELSE entry->>'text' END AS text,"
    "  to_timestamp(mtime / CASE WHEN mtime > 1e12 THEN 1000 ELSE 1 END) AS at, seq"
    "  FROM claude_session_store WHERE project_key = $1 AND session_id = $2"
    "  AND subpath = '' AND entry->>'type' IN ('user', 'assistant')"
    " UNION ALL"
    " SELECT provider, CASE kind WHEN 'prompt' THEN 'user' ELSE 'assistant' END,"
    "  entry->>'text', at, seq FROM aire_agent_log WHERE project_key = $1 AND session_id = $2"
    "  AND (kind = 'prompt' OR (kind = 'item.completed' AND entry->>'type' = 'agent_message'))"
    ") t WHERE text ~ '\\S' ORDER BY at DESC, seq DESC LIMIT $3"
)


def project_key(project: str) -> str:
    """The casita's key, derived as the engine derives it — without creating the casita."""
    return project_key_for_directory(str(WORKSPACES / project))


async def sessions(project: str) -> list[dict]:
    """Every session the casita holds, newest activity first."""
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        rows = await _fetch_or_empty(conn, _SESSIONS, project_key(project))
    out = [{"session": r["session_id"], "provider": r["provider"], "entries": r["entries"],
            "first_at": r["first_at"].isoformat(), "last_at": r["last_at"].isoformat()} for r in rows]
    return sorted(out, key=lambda s: s["last_at"], reverse=True)


async def turns(project: str, session: str, limit: int = MAX_TURNS) -> list[dict]:
    """The last `limit` spoken turns of one session, oldest first, as {at, role, text}."""
    bounded = max(1, min(limit, MAX_TURNS))
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        rows = await _fetch_or_empty(conn, _TURNS, project_key(project), sdk_session_uuid(session), bounded)
    return [{"at": r["at"].isoformat(), "role": r["role"], "provider": r["src"], "text": r["text"]}
            for r in reversed(rows)]


async def _fetch_or_empty(conn: Any, sql: str, *args: Any) -> list[Any]:
    """A box where one of the two tables was never created reads as no chats, not
    as an error — the same tolerance `recall` learned on the droplet (#54)."""
    import asyncpg

    try:
        return await conn.fetch(sql, *args)
    except asyncpg.UndefinedTableError:
        return []
