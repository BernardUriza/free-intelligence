"""SDK MCP server — direct Postgres queries for the agent (F4, v3.9.51).

Background: the `persona-runner` agent previously read user facts, recent
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
            "SELECT category, fact, updated_at FROM principal_facts "
            "WHERE principal_id = $1 AND deleted_at IS NULL "
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
    from khimeras_shared.deep_memory import query_user_memory

    user_id = (args.get("user_id") or "").strip()
    query = (args.get("query") or "").strip()
    if not user_id or not query:
        return _error("user_id and query are required")
    # Reserved synthetic namespaces are NOT user memory and must never be
    # reachable through this agent-facing tool. `__chatgpt_archive__` holds
    # Bernard's intimate ChatGPT history (health/sexuality/sensitive) that was
    # DELIBERATELY routed out of auto-recall (hybrid privacy choice, 2026-06-03);
    # `__corpus_film__` is shared topic knowledge with its own retrieval path
    # (query_corpus). Real users are Discord snowflakes — a `__`-prefixed id can
    # only be an attempt (by the model or a crafted message) to read an archive
    # that must stay out of any public turn.
    if user_id.startswith("__"):
        return _error(f"'{user_id}' is a reserved namespace, not a user — not accessible here")
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
    from khimeras_shared.html_artifacts import insert_artifact

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
    # The URL must point at a host that actually serves `/a/{id}` — the runner
    # itself does (persona_runner.api.artifacts). NO hardcoded default: the old
    # one was `discord-bot.nicecliff…`, a host that is now NXDOMAIN (and the
    # greendune discord-bot is scaled to zero), so an unconfigured base minted a
    # dead link and reported it as "Published" — a fake-green. Fail loud instead;
    # the artifact IS saved, so the id is returned for recovery.
    base = (os.environ.get("ARTIFACT_BASE_URL") or "").rstrip("/")
    if not base:
        log.error("artifact_base_url_unconfigured", artifact_id=artifact_id)
        return _error(
            f"Artifact saved (id={artifact_id}) but ARTIFACT_BASE_URL is not configured, "
            f"so I can't give you a live link. Set it to the runner's public URL."
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


# ─── Agent self-knowledge (agent_facts, v4.20.14 PR-1) ──────────────────
# These are the FIRST write-capable tools in this server. They operate on
# `agent_facts` — what the bot knows about ITSELF — never on `principal_facts`
# (user facts). Scope is storage CRUD only; auto-extraction of self-facts from
# the conversation is PR-2 and lives nowhere yet.

_PROVENANCE_VALUES = ("self_declared", "user_attributed", "system_prompt", "consolidation")


@tool(
    "get_agent_facts",
    (
        "Return what an AGENT knows about ITSELF (not about a user) — the bot's "
        "own accumulated self-facts from the `agent_facts` table, newest first. "
        "Call this at the start of a turn with agent_id='insult' to ground who "
        "you are. Optional `category` filters to one category. One fact per line."
    ),
    {"agent_id": str, "category": str},
)
async def get_agent_facts(args: dict) -> dict:
    agent_id = (args.get("agent_id") or "").strip()
    if not agent_id:
        return _error("agent_id is required")
    category = (args.get("category") or "").strip()
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        if category:
            rows = await conn.fetch(
                "SELECT id, category, fact, provenance, updated_at FROM agent_facts "
                "WHERE agent_id = $1 AND category = $2 AND deleted_at IS NULL "
                "ORDER BY updated_at DESC",
                agent_id,
                category,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, category, fact, provenance, updated_at FROM agent_facts "
                "WHERE agent_id = $1 AND deleted_at IS NULL "
                "ORDER BY updated_at DESC",
                agent_id,
            )
        if not rows:
            return _text(f"No self-facts on file for agent {agent_id}.")
        lines = [f"# Self-facts for agent {agent_id} ({len(rows)} total)"]
        for r in rows:
            cat = r["category"] or "uncategorized"
            lines.append(f"- [{r['id']}] [{cat}] ({r['provenance']}) {r['fact']}")
        return _text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "add_agent_fact",
    (
        "Record a NEW self-fact for an agent in `agent_facts`. Use when the bot "
        "learns something durable about itself worth remembering across turns. "
        "`provenance` MUST be one of: self_declared, user_attributed, "
        "system_prompt, consolidation. Returns the new fact id."
    ),
    {"agent_id": str, "fact": str, "category": str, "provenance": str},
)
async def add_agent_fact(args: dict) -> dict:
    agent_id = (args.get("agent_id") or "").strip()
    fact = (args.get("fact") or "").strip()
    category = (args.get("category") or "general").strip() or "general"
    provenance = (args.get("provenance") or "").strip()
    if not agent_id or not fact:
        return _error("agent_id and fact are required")
    if provenance not in _PROVENANCE_VALUES:
        return _error(f"provenance must be one of {', '.join(_PROVENANCE_VALUES)}")
    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        new_id = await conn.fetchval(
            "INSERT INTO agent_facts (agent_id, fact, category, provenance, updated_at) "
            "VALUES ($1, $2, $3, $4, extract(epoch from now())) RETURNING id",
            agent_id,
            fact,
            category,
            provenance,
        )
        return _text(f"Stored self-fact {new_id} for agent {agent_id}.")
    except asyncpg.ForeignKeyViolationError:
        return _error(f"Unknown agent_id '{agent_id}' (not in agents table).")
    finally:
        await conn.close()


@tool(
    "update_agent_fact",
    (
        "Edit an existing self-fact by id. Provide only the fields you want to "
        "change — `fact`, `category`, and/or `provenance`. Set `delete` true to "
        "soft-delete the fact instead. Bumps updated_at on any change."
    ),
    {"fact_id": int, "fact": str, "category": str, "provenance": str, "delete": bool},
)
async def update_agent_fact(args: dict) -> dict:
    raw_id = args.get("fact_id")
    try:
        fact_id = int(raw_id)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return _error("fact_id is required and must be an integer")

    if args.get("delete"):
        conn = await _connect()
        if conn is None:
            return _error("Postgres unreachable")
        try:
            status = await conn.execute(
                "UPDATE agent_facts SET deleted_at = extract(epoch from now()), "
                "updated_at = extract(epoch from now()) WHERE id = $1 AND deleted_at IS NULL",
                fact_id,
            )
            if status.endswith("0"):
                return _error(f"No active self-fact with id {fact_id}.")
            return _text(f"Soft-deleted self-fact {fact_id}.")
        finally:
            await conn.close()

    sets: list[str] = []
    params: list = []
    if fact := (args.get("fact") or "").strip():
        params.append(fact)
        sets.append(f"fact = ${len(params)}")
    if category := (args.get("category") or "").strip():
        params.append(category)
        sets.append(f"category = ${len(params)}")
    if provenance := (args.get("provenance") or "").strip():
        if provenance not in _PROVENANCE_VALUES:
            return _error(f"provenance must be one of {', '.join(_PROVENANCE_VALUES)}")
        params.append(provenance)
        sets.append(f"provenance = ${len(params)}")
    if not sets:
        return _error("Nothing to update — pass fact, category, provenance, or delete.")
    sets.append("updated_at = extract(epoch from now())")
    params.append(fact_id)

    conn = await _connect()
    if conn is None:
        return _error("Postgres unreachable")
    try:
        # `sets` is built only from hardcoded "col = $N" fragments above — no
        # user input reaches the SQL string; all values go through *params.
        status = await conn.execute(
            f"UPDATE agent_facts SET {', '.join(sets)} WHERE id = ${len(params)} AND deleted_at IS NULL",  # noqa: S608
            *params,
        )
        if status.endswith("0"):
            return _error(f"No active self-fact with id {fact_id}.")
        return _text(f"Updated self-fact {fact_id}.")
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
    get_agent_facts,
    add_agent_fact,
    update_agent_fact,
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
