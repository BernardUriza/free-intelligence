"""MCP tools over `agent_facts` — the bot's self-knowledge (v4.20.14 PR-1).

These are the FIRST write-capable tools in this server. They operate on
`agent_facts` — what the bot knows about ITSELF — never on `principal_facts`
(user facts). Scope is storage CRUD only; auto-extraction of self-facts from
the conversation lives in the gateway's reflection worker.
"""

from __future__ import annotations

import asyncpg

from persona_runner.mcp_tools import shared
from persona_runner.mcp_tools.tooldef import tool

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
        return shared._error("agent_id is required")
    category = (args.get("category") or "").strip()
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
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
            return shared._text(f"No self-facts on file for agent {agent_id}.")
        lines = [f"# Self-facts for agent {agent_id} ({len(rows)} total)"]
        for r in rows:
            cat = r["category"] or "uncategorized"
            lines.append(f"- [{r['id']}] [{cat}] ({r['provenance']}) {r['fact']}")
        return shared._text("\n".join(lines))
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
        return shared._error("agent_id and fact are required")
    if provenance not in _PROVENANCE_VALUES:
        return shared._error(f"provenance must be one of {', '.join(_PROVENANCE_VALUES)}")
    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
    try:
        new_id = await conn.fetchval(
            "INSERT INTO agent_facts (agent_id, fact, category, provenance, updated_at) "
            "VALUES ($1, $2, $3, $4, extract(epoch from now())) RETURNING id",
            agent_id,
            fact,
            category,
            provenance,
        )
        return shared._text(f"Stored self-fact {new_id} for agent {agent_id}.")
    except asyncpg.ForeignKeyViolationError:
        return shared._error(f"Unknown agent_id '{agent_id}' (not in agents table).")
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
        return shared._error("fact_id is required and must be an integer")

    if args.get("delete"):
        conn = await shared._connect()
        if conn is None:
            return shared._error("Postgres unreachable")
        try:
            status = await conn.execute(
                "UPDATE agent_facts SET deleted_at = extract(epoch from now()), "
                "updated_at = extract(epoch from now()) WHERE id = $1 AND deleted_at IS NULL",
                fact_id,
            )
            if status.endswith("0"):
                return shared._error(f"No active self-fact with id {fact_id}.")
            return shared._text(f"Soft-deleted self-fact {fact_id}.")
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
            return shared._error(f"provenance must be one of {', '.join(_PROVENANCE_VALUES)}")
        params.append(provenance)
        sets.append(f"provenance = ${len(params)}")
    if not sets:
        return shared._error("Nothing to update — pass fact, category, provenance, or delete.")
    sets.append("updated_at = extract(epoch from now())")
    params.append(fact_id)

    conn = await shared._connect()
    if conn is None:
        return shared._error("Postgres unreachable")
    try:
        # `sets` is built only from hardcoded "col = $N" fragments above — no
        # user input reaches the SQL string; all values go through *params.
        status = await conn.execute(
            f"UPDATE agent_facts SET {', '.join(sets)} WHERE id = ${len(params)} AND deleted_at IS NULL",  # noqa: S608
            *params,
        )
        if status.endswith("0"):
            return shared._error(f"No active self-fact with id {fact_id}.")
        return shared._text(f"Updated self-fact {fact_id}.")
    finally:
        await conn.close()
