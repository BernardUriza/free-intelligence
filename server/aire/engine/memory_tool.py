"""The `memory` in-process MCP server — the agent recalls its OWN transcript.

The first tenant of AIRE's tool registry (backlog #29). An in-process SDK MCP
server (runs INSIDE the daemon, no subprocess) exposing one tool, `recall`, that
searches this project's mirrored transcript in `claude_session_store` and returns
the matching entries. It is the agent reading its own memory — the same sanctioned
exception to [[write-only-daemon]] as `session_store.load()`, never a waiter read.

SESSION-SCOPED by construction: `build_memory_server` closes over the project_key,
so `recall` only ever sees THIS project's rows. The wire never passes a key, so
one project can never read another's memory.
"""

from __future__ import annotations

import os
from typing import Any

import asyncpg
from claude_agent_sdk import create_sdk_mcp_server, tool

_TABLE = "claude_session_store"
_MAX_LIMIT = 20
_SNIPPET = 500
# `recall` is an ILIKE over `entry::text` — no index can serve it, so its cost
# grows linearly with the transcript, which is the one thing AIRE guarantees
# will grow forever. It runs INSIDE a paid turn, so an unbounded one does not
# fail: it stalls, and the bill keeps running. Both bounds are deliberate — a
# connect that can hang forever (every sibling call site passes a timeout; this
# one did not) and a scan that can outlive the caller's patience.
_CONNECT_TIMEOUT_S = 10
_STATEMENT_TIMEOUT_MS = 5_000


def _text(payload: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": payload}]}


def _error(msg: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}


def _clamp(raw: Any, default: int) -> int:
    try:
        return max(1, min(_MAX_LIMIT, int(raw)))
    except (TypeError, ValueError):
        return default


async def _search(project_key: str, query: str, limit: int) -> list[str]:
    """The matching transcript entries for this project, newest first."""
    conn = await asyncpg.connect(os.environ.get("AIRE_DATABASE_URL", ""),
                                 timeout=_CONNECT_TIMEOUT_S,
                                 server_settings={"statement_timeout": str(_STATEMENT_TIMEOUT_MS)})
    try:
        rows = await conn.fetch(
            f"SELECT seq, entry::text AS body FROM {_TABLE} "
            "WHERE project_key = $1 AND entry::text ILIKE $2 "
            "ORDER BY seq DESC LIMIT $3",
            project_key, f"%{query}%", limit,
        )
    finally:
        await conn.close()
    return [f"[seq {r['seq']}] {r['body'][:_SNIPPET]}" for r in rows]


def build_memory_server(project_key: str, _cwd: str = "") -> Any:
    """The session-scoped `memory` server: `recall` over THIS project's transcript.
    (`_cwd` is the registry's shared factory contract; this tool is database-backed
    and does not touch the casita's disk.)"""

    @tool(
        "recall",
        "Search your own past transcript in this project for entries matching a "
        "query (case-insensitive substring), to remember something said in an "
        "earlier session. Returns the matching entries, newest first.",
        {"query": str, "limit": int},
    )
    async def recall(args: dict[str, Any]) -> dict[str, Any]:
        query = (args.get("query") or "").strip()
        if not query:
            return _error("query is required")
        try:
            hits = await _search(project_key, query, _clamp(args.get("limit"), 5))
        except Exception as exc:  # noqa: BLE001 — a tool reports its failure as text
            return _error(f"recall failed: {type(exc).__name__}")
        return _text("\n\n".join(hits) if hits else f"No past entries match {query!r}.")

    return create_sdk_mcp_server(name="memory", version="1.0.0", tools=[recall])
