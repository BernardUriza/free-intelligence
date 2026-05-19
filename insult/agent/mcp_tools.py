"""SDK MCP server — direct Postgres queries for the agent (F4, v3.9.51).

Background: the `insult-runner` agent previously read user facts, recent
messages and disclosure logs from markdown files under
`/data/insult-workspace/`. Those files were produced every 60 s by
`workspace_renderer.py` from the same Postgres tables that store the
real data. The renderer was a 264-line projector that existed only so
the agent's built-in `Read`/`Grep`/`Glob` tools could see PG state.

This module ships a set of in-process MCP tools that hit Postgres
directly. The agent calls them as `mcp__insult_db__get_facts` instead
of `Read("facts/{user_id}.md")`. Benefits:

- No staleness window (markdown was 0-60s behind PG).
- No projector process or SMB workspace mount to maintain.
- The agent receives structured data (cleaner inputs than markdown).
- One fewer moving piece in the data path (POST-DEPLOY-1 already
  removed the SQLite blob; this removes the markdown projection).

Architecture mirrors `pg_state.py`: one-shot asyncpg connections per
tool call. The agent invokes tools rarely enough (a few per turn) that
a shared pool is overkill and would force coupling to the runner's
event loop lifecycle.

Migration path:
- v3.9.51: ship this module + register tools alongside `Read/Grep/Glob`.
  Agent can use either; persona is unchanged.
- v3.9.52: persona steered to prefer MCP tools; `Read/Grep/Glob` still
  allowed as fallback during validation.
- v3.9.53: `Read/Grep/Glob` removed from `allowed_tools`; workspace
  mount + renderer process decommissioned.
"""

from __future__ import annotations

import os

import asyncpg
import structlog
from claude_agent_sdk import create_sdk_mcp_server, tool

log = structlog.get_logger()


async def _connect() -> asyncpg.Connection | None:
    """One-shot Postgres connection. Returns None when PG is unreachable."""
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        return await asyncpg.connect(url)
    except Exception:
        log.exception("mcp_tools_pg_connect_failed")
        return None


def _text(payload: str) -> dict:
    """Wrap a string into the MCP tool-result content envelope."""
    return {"content": [{"type": "text", "text": payload}]}


def _error(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}], "is_error": True}


# ─── Tools ─────────────────────────────────────────────────────────────


@tool(
    "get_user_facts",
    (
        "Return everything Insult knows about a specific user — their accumulated "
        "facts from prior conversations, grouped by category. Use this whenever you "
        "need to ground a response in what you already know about the person you're "
        "addressing. Returns one fact per line."
    ),
    {"user_id": str},
)
async def get_user_facts(args: dict) -> dict:
    user_id = (args.get("user_id") or "").strip()
    if not user_id:
        return _error("user_id is required")
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT category, fact, updated_at FROM user_facts "
            "WHERE user_id = $1 AND deleted_at IS NULL "
            "ORDER BY updated_at DESC",
            user_id,
        )
        if not rows:
            return _text(f"No facts on file for user {user_id}.")
        lines = [f"# Facts for user {user_id} ({len(rows)} total)"]
        for r in rows:
            cat = r["category"] or "uncategorized"
            lines.append(f"- [{cat}] {r['fact']}")
        return _text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "get_recent_messages",
    (
        "Return the last N messages in a channel (chronological, oldest first). "
        "Use when you need fresh context about what was just said. Default limit "
        "is 50 — keep it low unless you really need more."
    ),
    {"channel_id": str, "limit": int},
)
async def get_recent_messages(args: dict) -> dict:
    channel_id = (args.get("channel_id") or "").strip()
    if not channel_id:
        return _error("channel_id is required")
    limit = max(1, min(int(args.get("limit") or 50), 200))
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
            channel_id,
            limit,
        )
        rows = list(reversed(rows))  # oldest first
        if not rows:
            return _text(f"No messages found in channel {channel_id}.")
        lines = [f"# Last {len(rows)} messages in channel {channel_id}"]
        for r in rows:
            speaker = r["user_name"] or "?"
            lines.append(f"**{speaker}**: {r['content']}")
        return _text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "search_messages",
    (
        "Full-text search across a channel's message history. Use when you "
        "need to recall a specific topic the user mentioned earlier but it's "
        "not in the recent window. Returns matched messages with timestamps."
    ),
    {"channel_id": str, "query": str, "limit": int},
)
async def search_messages(args: dict) -> dict:
    channel_id = (args.get("channel_id") or "").strip()
    query = (args.get("query") or "").strip()
    if not channel_id or not query:
        return _error("channel_id and query are required")
    limit = max(1, min(int(args.get("limit") or 10), 50))
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT user_name, content, timestamp FROM messages "
            "WHERE channel_id = $1 AND content ILIKE $2 "
            "ORDER BY timestamp DESC LIMIT $3",
            channel_id,
            f"%{query}%",
            limit,
        )
        if not rows:
            return _text(f"No messages matching '{query}' in channel {channel_id}.")
        lines = [f"# {len(rows)} matches for '{query}' in channel {channel_id}"]
        for r in rows:
            speaker = r["user_name"] or "?"
            lines.append(f"**{speaker}** ({int(r['timestamp'])}): {r['content']}")
        return _text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "get_disclosure_log",
    (
        "Return clinical/emotional disclosures recorded for a user (CPTSD, "
        "medication, crisis events, etc.). Use when calibrating tone — high "
        "recent severity means soften the abrasive register."
    ),
    {"user_id": str, "days": int},
)
async def get_disclosure_log(args: dict) -> dict:
    user_id = (args.get("user_id") or "").strip()
    if not user_id:
        return _error("user_id is required")
    import time

    days = max(1, min(int(args.get("days") or 30), 365))
    cutoff = time.time() - days * 86400
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT category, severity, signals, timestamp "
            "FROM disclosure_log WHERE user_id = $1 AND timestamp >= $2 "
            "ORDER BY timestamp DESC",
            user_id,
            cutoff,
        )
        if not rows:
            return _text(f"No disclosures for user {user_id} in last {days}d.")
        lines = [f"# Disclosures for user {user_id} (last {days}d, {len(rows)} entries)"]
        for r in rows:
            ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r["timestamp"]))
            lines.append(f"- {ts_iso} | sev={r['severity']} | category={r['category']} | signals={r['signals']}")
        return _text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "deep_memory",
    (
        "Vector-search the user's longitudinal memory for semantically "
        "related chunks. Use when get_user_facts is too coarse — when you "
        "remember the user mentioning something specific but you need the "
        "actual phrasing, the context around it, or related fragments "
        "across conversations. Returns up to top_k chunks with similarity "
        "scores (0.0-1.0) and timestamps. Default top_k is 5; raise to 10 "
        "for broader recall, lower to 3 for precision."
    ),
    {"user_id": str, "query": str, "top_k": int},
)
async def deep_memory(args: dict) -> dict:
    from insult.core.deep_memory import query_user_memory

    user_id = (args.get("user_id") or "").strip()
    query = (args.get("query") or "").strip()
    if not user_id or not query:
        return _error("user_id and query are required")
    top_k = max(1, min(int(args.get("top_k") or 5), 20))
    results = await query_user_memory(user_id=user_id, query=query, top_k=top_k)
    if not results:
        return _text(
            f"No deep memory chunks found for user {user_id} matching '{query}'. "
            "Either nothing's been ingested for this user yet, or the query is too "
            "off-topic. Try get_user_facts for the structured fact list."
        )
    lines = [f"# {len(results)} deep-memory chunks for user {user_id} matching '{query}'"]
    for r in results:
        ts_iso = r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if r["created_at"] else "?"
        lines.append(f"\n## sim={r['similarity']:.3f} | source={r['source_type']}/{r['source_ref']} | {ts_iso}")
        lines.append(r["chunk_text"])
    return _text("\n".join(lines))


@tool(
    "publish_html_artifact",
    (
        "Publish a standalone HTML page (report, mini-app, snapshot, "
        "visualization) and return a shareable URL. Use when the response "
        "would be too long for chat, when the user asks for a visualization "
        "or interactive widget, when you want to share a structured document. "
        "Includes everything inline (CSS, JS) — no external assets fetched. "
        "URL is permanent; anyone with the link can view. "
        "Do NOT publish anything containing secrets, tokens, or private content "
        "the user wouldn't share publicly."
    ),
    {"title": str, "html_content": str, "user_id": str},
)
async def publish_html_artifact(args: dict) -> dict:
    from insult.core.html_artifacts import insert_artifact

    title = (args.get("title") or "").strip()
    html_content = args.get("html_content") or ""
    user_id = (args.get("user_id") or "").strip() or None
    if not title:
        return _error("title is required")
    if not html_content:
        return _error("html_content is required")
    if len(html_content) > 1_000_000:
        return _error("html_content too large (max 1MB)")
    artifact_id = await insert_artifact(title=title, html_content=html_content, created_by_user_id=user_id)
    if artifact_id is None:
        return _error("Failed to persist artifact (Postgres unreachable or insert failed)")
    base = os.environ.get(
        "ARTIFACT_BASE_URL",
        "https://discord-bot.nicecliff-10074f57.eastus.azurecontainerapps.io",
    )
    url = f"{base}/a/{artifact_id}"
    return _text(f"Published. URL: {url}\nTitle: {title}\nSize: {len(html_content)} bytes")


@tool(
    "get_emotional_arc",
    (
        "Return the current emotional-arc state for a user in a channel "
        "(phase, recovery_signals, turns_in_phase). Use when deciding whether "
        "to lean abrasive or hold space."
    ),
    {"user_id": str, "channel_id": str},
)
async def get_emotional_arc(args: dict) -> dict:
    user_id = (args.get("user_id") or "").strip()
    channel_id = (args.get("channel_id") or "").strip()
    if not user_id or not channel_id:
        return _error("user_id and channel_id are required")
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        row = await conn.fetchrow(
            "SELECT phase, intensity, recovery_signals, turns_in_phase, updated_at "
            "FROM emotional_arcs WHERE user_id = $1 AND channel_id = $2",
            user_id,
            channel_id,
        )
        if row is None:
            return _text(f"No emotional arc tracked for user {user_id} in channel {channel_id}.")
        return _text(
            f"# Emotional arc — user {user_id} / channel {channel_id}\n"
            f"phase: {row['phase']}\n"
            f"intensity: {row['intensity']}\n"
            f"recovery_signals: {row['recovery_signals']}\n"
            f"turns_in_phase: {row['turns_in_phase']}"
        )
    finally:
        await conn.close()


# ─── Server ────────────────────────────────────────────────────────────


INSULT_DB_TOOLS = [
    get_user_facts,
    get_recent_messages,
    search_messages,
    get_disclosure_log,
    deep_memory,
    publish_html_artifact,
    get_emotional_arc,
]

# Name used in `allowed_tools`: `mcp__insult_db__<tool_name>`
INSULT_DB_SERVER_NAME = "insult_db"


def build_insult_db_server():
    """Return the McpSdkServerConfig the runner registers in ClaudeAgentOptions.

    Called once per session at client construction. The server itself is
    stateless — each tool opens its own connection per invocation, matching
    the pg_state pattern. No shared pool to leak across sessions.
    """
    return create_sdk_mcp_server(
        name=INSULT_DB_SERVER_NAME,
        version="1.0.0",
        tools=INSULT_DB_TOOLS,
    )
