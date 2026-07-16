"""Agent self-knowledge — the `agent_facts` table, gateway side.

What a persona knows about ITSELF (never about users — that is
`principal_facts`). The runner's MCP tools own the in-turn CRUD; this
repository is the REFLECTION path: the weekly worker reads the existing
self-facts, asks the judge what deserves permanence, and appends the chosen
tastes with `provenance='self_declared'`. ADD-only by construction — the
reflection loop has no delete path at all.

`agent_facts.agent_id` has an FK to `agents(name)`, so every write first
upserts the agent row; `agents.last_reflected_at` is the durable cadence gate
(an in-process timestamp would reset on every deploy).
"""

from __future__ import annotations

import time

import structlog

from khimeras_shared.memory.base import BaseRepository

log = structlog.get_logger()

PROVENANCE_VALUES = ("self_declared", "user_attributed", "system_prompt", "consolidation")


class AgentFactsRepository(BaseRepository):
    """Owns the reflection-side access to `agent_facts` + the agents gate."""

    async def get_self_facts(self, agent_id: str, limit: int = 60) -> list[dict]:
        """Live self-facts for one agent, newest first. Empty list on failure —
        reflection is best-effort and must never take a persona down."""
        try:
            rows = await self._fetch(
                "SELECT id, category, fact, provenance, updated_at FROM agent_facts "
                "WHERE agent_id = $1 AND deleted_at IS NULL "
                "ORDER BY updated_at DESC LIMIT $2",
                agent_id,
                limit,
            )
            return [dict(r) for r in rows]
        except Exception:
            log.exception("agent_facts_read_failed", agent_id=agent_id)
            return []

    async def add_self_fact(self, agent_id: str, fact: str, category: str, provenance: str) -> int | None:
        """Append one self-fact (upserting the agents row the FK requires).
        Returns the new id, or None on failure/invalid provenance."""
        if provenance not in PROVENANCE_VALUES:
            log.error("agent_fact_bad_provenance", agent_id=agent_id, provenance=provenance)
            return None
        try:
            await self._ensure_agent(agent_id)
            new_id = await self._fetchval(
                "INSERT INTO agent_facts (agent_id, fact, category, provenance, updated_at) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                agent_id,
                fact,
                category or "general",
                provenance,
                time.time(),
            )
            return int(new_id) if new_id is not None else None
        except Exception:
            log.exception("agent_fact_write_failed", agent_id=agent_id)
            return None

    async def get_last_reflected_at(self, agent_id: str) -> float | None:
        """The durable reflection gate. None = never reflected (or agent row absent)."""
        try:
            return await self._fetchval("SELECT last_reflected_at FROM agents WHERE name = $1", agent_id)
        except Exception:
            log.exception("agent_reflected_read_failed", agent_id=agent_id)
            return None

    async def mark_reflected(self, agent_id: str, ts: float) -> None:
        """Advance the cadence gate (upserting the agents row if needed)."""
        try:
            await self._ensure_agent(agent_id)
            await self._execute("UPDATE agents SET last_reflected_at = $2 WHERE name = $1", agent_id, ts)
        except Exception:
            log.exception("agent_reflected_mark_failed", agent_id=agent_id)

    async def _ensure_agent(self, agent_id: str) -> None:
        await self._execute(
            "INSERT INTO agents (name, created_at) VALUES ($1, $2) ON CONFLICT (name) DO NOTHING",
            agent_id,
            time.time(),
        )
