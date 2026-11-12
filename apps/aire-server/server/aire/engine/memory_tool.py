"""The `memory` in-process MCP server — the agent recalls its OWN transcript.

The first tenant of AIRE's tool registry (backlog #29). An in-process SDK MCP
server exposing one tool, `recall`, that searches this project's mirrored
transcript and returns the matching entries. The transcript lives in TWO tables:
`claude_session_store` (the Claude SDK's own store) and `aire_agent_log` (the pen
the daemon holds for Codex and every ACP agent, `acp_mirror`). `recall` reads
both, so a casita remembers what it said whichever backend answered (#54). The
Codex backend reaches this same server over stdio (`engine/stdio_tool.py`).
It is the agent reading its own memory — the same sanctioned
exception to [[write-only-daemon]] as `session_store.load()`, never a waiter read.

SESSION-SCOPED by construction: `build_memory_server` closes over the project_key,
so `recall` only ever sees THIS project's rows. The wire never passes a key, so
one project can never read another's memory.
"""

from __future__ import annotations

from typing import Any

from ..agent_sdk import mcp_server as create_sdk_mcp_server
from ..agent_sdk import tool

from .. import acp_mirror, db

_TABLE = "claude_session_store"
_MAX_LIMIT = 20
_SNIPPET = 500
# `recall` is an ILIKE over `entry::text` — no index can serve it, so its cost
# grows linearly with the transcript, which is the one thing AIRE guarantees
# will grow forever. It runs INSIDE a paid turn, so an unbounded one does not
# fail: it stalls, and the bill keeps running. The connect bound now comes from
# the shared pool; this one is the scan's, and it rides as SET LOCAL inside a
# transaction so it governs THIS query and never the next borrower's.
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


_STORE_HITS = (
    f" SELECT 'claude' AS src, seq, entry::text AS body, mtime AS ms FROM {_TABLE}"
    "  WHERE project_key = $1 AND entry::text ILIKE $2"
    " UNION ALL"
)
_AGENT_HITS = (
    " SELECT provider AS src, seq, entry::text AS body,"
    " (extract(epoch FROM at) * 1000)::bigint AS ms"
    f" FROM {acp_mirror.TABLE}"
    "  WHERE project_key = $1 AND entry::text ILIKE $2"
)


def _search_sql(has_store: bool) -> str:
    """The SDK store exists only once a Claude turn created it; a Codex-only box has none."""
    head = _STORE_HITS if has_store else ""
    return f"SELECT src, seq, body FROM ({head}{_AGENT_HITS}) hits ORDER BY ms DESC, seq DESC LIMIT $3"


async def _search(project_key: str, query: str, limit: int) -> list[str]:
    """The matching transcript entries for this project from both tables,
    newest first by wall clock (the two `seq` columns are separate counters)."""
    await acp_mirror.ensure()
    async with db.acquire(statement_timeout_ms=_STATEMENT_TIMEOUT_MS) as conn:
        has_store = await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", _TABLE)
        rows = await conn.fetch(_search_sql(has_store), project_key, f"%{query}%", limit)
    return [f"[{r['src']} seq {r['seq']}] {r['body'][:_SNIPPET]}" for r in rows]


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
