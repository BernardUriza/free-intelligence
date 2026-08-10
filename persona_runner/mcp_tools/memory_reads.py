"""Read-only MCP tools over the memory data plane — facts, messages, disclosures, arcs.

Ninguna de estas tools recibe `user_id` ni `channel_id`: los toma del principal
atado por el servidor para ESE turno (`turn_context`). No es cosmética de
firmas — es la diferencia entre un gate de capacidades y una autorización.
Mientras la identidad era un parámetro, el modelo podía nombrar a cualquiera, y
el 2026-08-10 lo hizo: le atribuyó a Bernard un fact de Alex y le habló de la
muerte de su madre, que está viva. Los dos ids son snowflakes legítimos, así que
validar el formato no habría cambiado nada. La identidad la pone el servidor o
no es identidad.
"""

from __future__ import annotations

from claude_agent_sdk import tool

from persona_runner.mcp_tools import shared
from persona_runner.mcp_tools.turn_context import current_principal


@tool(
    "get_user_facts",
    (
        "Return everything you know about the person you are talking to right now — "
        "their accumulated facts from prior conversations, grouped by category. Use "
        "this whenever you need to ground a response in what you already know about "
        "them. Returns one fact per line. It always reads the user of the current "
        "turn; there is no way to ask about somebody else, by design."
    ),
    {},
)
async def get_user_facts(args: dict) -> dict:
    user_id = current_principal().user_id
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT category, fact, updated_at FROM principal_facts "
            "WHERE principal_id = $1 AND deleted_at IS NULL "
            "ORDER BY updated_at DESC",
            user_id,
        )
        if not rows:
            return shared._text(f"No facts on file for user {user_id}.")
        lines = [f"# Facts for user {user_id} ({len(rows)} total)"]
        for r in rows:
            cat = r["category"] or "uncategorized"
            lines.append(f"- [{cat}] {r['fact']}")
        return shared._text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "get_recent_messages",
    (
        "Return the last N messages in THIS channel (chronological, oldest first). "
        "Use when you need fresh context about what was just said. Default limit "
        "is 50 — keep it low unless you really need more. Always the current "
        "channel; other channels, including other people's DMs, are not reachable."
    ),
    {"limit": int},
)
async def get_recent_messages(args: dict) -> dict:
    channel_id = current_principal().channel_id
    limit = max(1, min(int(args.get("limit") or 50), 200))
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
            channel_id,
            limit,
        )
        rows = list(reversed(rows))  # oldest first
        if not rows:
            return shared._text(f"No messages found in channel {channel_id}.")
        lines = [f"# Last {len(rows)} messages in channel {channel_id}"]
        for r in rows:
            speaker = r["user_name"] or "?"
            lines.append(f"**{speaker}**: {r['content']}")
        return shared._text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "search_messages",
    (
        "Full-text search across a channel's message history. Use when you "
        "need to recall a specific topic the user mentioned earlier but it's "
        "not in the recent window. Returns matched messages with timestamps."
    ),
    {"query": str, "limit": int},
)
async def search_messages(args: dict) -> dict:
    channel_id = current_principal().channel_id
    query = (args.get("query") or "").strip()
    if not query:
        return shared._error("query is required")
    limit = max(1, min(int(args.get("limit") or 10), 50))
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
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
            return shared._text(f"No messages matching '{query}' in channel {channel_id}.")
        lines = [f"# {len(rows)} matches for '{query}' in channel {channel_id}"]
        for r in rows:
            speaker = r["user_name"] or "?"
            lines.append(f"**{speaker}** ({int(r['timestamp'])}): {r['content']}")
        return shared._text("\n".join(lines))
    finally:
        await conn.close()


@tool(
    "get_disclosure_log",
    (
        "Return clinical/emotional disclosures recorded for a user (CPTSD, "
        "medication, crisis events, etc.). Use when calibrating tone — high "
        "recent severity means soften the abrasive register."
    ),
    {"days": int},
)
async def get_disclosure_log(args: dict) -> dict:
    user_id = current_principal().user_id
    import time

    days = max(1, min(int(args.get("days") or 30), 365))
    cutoff = time.time() - days * 86400
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
    try:
        rows = await conn.fetch(
            "SELECT category, severity, signals, timestamp "
            "FROM disclosure_log WHERE user_id = $1 AND timestamp >= $2 "
            "ORDER BY timestamp DESC",
            user_id,
            cutoff,
        )
        if not rows:
            return shared._text(f"No disclosures for user {user_id} in last {days}d.")
        lines = [f"# Disclosures for user {user_id} (last {days}d, {len(rows)} entries)"]
        for r in rows:
            ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r["timestamp"]))
            lines.append(f"- {ts_iso} | sev={r['severity']} | category={r['category']} | signals={r['signals']}")
        return shared._text("\n".join(lines))
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
    {"query": str, "top_k": int},
)
async def deep_memory(args: dict) -> dict:
    from khimeras_shared.deep_memory import query_user_memory

    # El guard de namespaces reservados (`__chatgpt_archive__`, con el historial
    # íntimo de Bernard sacado a propósito del auto-recall en 2026-06-03) vivía
    # aquí como un `startswith("__")` sobre el parámetro. Ya no hace falta:
    # el id lo pone el servidor y es siempre un snowflake de Discord, así que no
    # hay parámetro que envenenar. Fue, además, la única defensa de este tipo en
    # las seis tools — pensada contra archivos sintéticos y nunca contra OTRA
    # PERSONA, que resultó ser el agujero real.
    user_id = current_principal().user_id
    query = (args.get("query") or "").strip()
    if not query:
        return shared._error("query is required")
    top_k = max(1, min(int(args.get("top_k") or 5), 20))
    results = await query_user_memory(user_id=user_id, query=query, top_k=top_k)
    if not results:
        return shared._text(
            f"No deep memory chunks found for user {user_id} matching '{query}'. "
            "Either nothing's been ingested for this user yet, or the query is too "
            "off-topic. Try get_user_facts for the structured fact list."
        )
    lines = [f"# {len(results)} deep-memory chunks for user {user_id} matching '{query}'"]
    for r in results:
        ts_iso = r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ") if r["created_at"] else "?"
        lines.append(f"\n## sim={r['similarity']:.3f} | source={r['source_type']}/{r['source_ref']} | {ts_iso}")
        lines.append(r["chunk_text"])
    return shared._text("\n".join(lines))


@tool(
    "get_emotional_arc",
    (
        "Return the current emotional-arc state for a user in a channel "
        "(phase, recovery_signals, turns_in_phase). Use when deciding whether "
        "to lean abrasive or hold space."
    ),
    {},
)
async def get_emotional_arc(args: dict) -> dict:
    principal = current_principal()
    user_id, channel_id = principal.user_id, principal.channel_id
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
    try:
        row = await conn.fetchrow(
            "SELECT phase, intensity, recovery_signals, turns_in_phase, updated_at "
            "FROM emotional_arcs WHERE user_id = $1 AND channel_id = $2",
            user_id,
            channel_id,
        )
        if row is None:
            return shared._text(f"No emotional arc tracked for user {user_id} in channel {channel_id}.")
        return shared._text(
            f"# Emotional arc — user {user_id} / channel {channel_id}\n"
            f"phase: {row['phase']}\n"
            f"intensity: {row['intensity']}\n"
            f"recovery_signals: {row['recovery_signals']}\n"
            f"turns_in_phase: {row['turns_in_phase']}"
        )
    finally:
        await conn.close()
