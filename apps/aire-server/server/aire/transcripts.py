"""A project's chats, read back as turns — for the agent that works on the project (#55).

The transcript lives in two tables: `claude_session_store` (the Claude SDK's own
store) and `aire_agent_log` (the pen for Codex and every ACP agent). `recall`
already searches both for words; this reads them as conversations — which
sessions a casita has, and what was said in one — so an agent outside the turn
(Claude Code through the projects MCP) can take a project's chats as context.

The read passes [[write-only-daemon]] on two counts: it feeds an agent, the
`recall` family, and the caller owns the rows (constant tokens only). What it
returns is the SPOKEN text, flattened — tool calls, attachments and usage stay
in the tables, where the front can render them.
"""

from __future__ import annotations

import json
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
    " FROM claude_session_store WHERE project_key = $1 GROUP BY session_id"
    " UNION ALL"
    " SELECT session_id, min(provider), count(*), min(at), max(at)"
    " FROM aire_agent_log WHERE project_key = $1 GROUP BY session_id"
)
_TURNS = (
    "SELECT * FROM ("
    " SELECT 'claude' AS src, NULL AS kind, entry::text AS body, to_timestamp(mtime /"
    "  CASE WHEN mtime > 1e12 THEN 1000 ELSE 1 END) AS at, seq FROM claude_session_store"
    "  WHERE project_key = $1 AND session_id = $2"
    " UNION ALL"
    " SELECT provider, kind, entry::text, at, seq FROM aire_agent_log"
    "  WHERE project_key = $1 AND session_id = $2 AND kind IN ('prompt', 'item.completed')"
    ") t ORDER BY at, seq"
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
    """What was said in one session, oldest first, as {at, role, text}."""
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        rows = await _fetch_or_empty(conn, _TURNS, project_key(project), sdk_session_uuid(session))
    spoken = [t for r in rows if (t := _spoken(r)) is not None]
    return spoken[-max(1, min(limit, MAX_TURNS)):]


async def _fetch_or_empty(conn: Any, sql: str, *args: Any) -> list[Any]:
    """A box where one of the two tables was never created reads as no chats, not
    as an error — the same tolerance `recall` learned on the droplet (#54)."""
    import asyncpg

    try:
        return await conn.fetch(sql, *args)
    except asyncpg.UndefinedTableError:
        return []


def _spoken(row: Any) -> dict | None:
    entry = json.loads(row["body"])
    role, text = (_from_sdk(entry) if row["src"] == "claude" else _from_agent(row["kind"], entry))
    if not text.strip():
        return None
    return {"at": row["at"].isoformat(), "role": role, "provider": row["src"], "text": text}


def _from_sdk(entry: dict) -> tuple[str, str]:
    role = entry.get("type", "")
    if role not in ("user", "assistant"):
        return role, ""
    content = (entry.get("message") or {}).get("content", entry.get("text", ""))
    if isinstance(content, str):
        return role, content
    return role, "\n".join(b.get("text", "") for b in content
                           if isinstance(b, dict) and b.get("type") == "text")


def _from_agent(kind: str, entry: dict) -> tuple[str, str]:
    if kind == "prompt":
        return "user", str(entry.get("text", ""))
    if entry.get("type") == "agent_message":
        return "assistant", str(entry.get("text", ""))
    return kind, ""
