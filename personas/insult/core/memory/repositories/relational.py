"""Relational state: emotional arcs, stance log, contradiction log.

These three tables share a domain (how the user is positioning themselves
over time) even though they have distinct schemas. Grouping them in a
single repository avoids having three near-empty repo files while keeping
the shared conceptual framing: "what has this user already committed to?"

- `emotional_arcs`: one row per (channel, user). Tracks phase transitions
  (crisis → recovery). Upserted every turn by the arc_tracker flow.
- `stance_log`: append-only with FIFO eviction (keep 20 per context).
  Stores topic-specific positions so the bot can cite "you said X last
  week" without replaying full transcripts.
- `contradiction_log`: append-only. Records detected prior/current-turn
  contradictions so the MEMORY_RECALL modifier can cash them in.

Migrated to asyncpg on 2026-05-12 PG migration. The stance-log FIFO
eviction subquery converted cleanly — Postgres supports the same
`DELETE WHERE id NOT IN (subquery)` shape SQLite uses.
"""

from __future__ import annotations

import time

import asyncpg
import structlog

from personas.insult.core.memory.base import BaseRepository

log = structlog.get_logger()


class RelationalStateRepository(BaseRepository):
    """Owns `emotional_arcs`, `stance_log`, and `contradiction_log`."""

    # -- Emotional arcs --

    async def get_arc(self, channel_id: str, user_id: str) -> dict | None:
        row = await self._fetchrow(
            "SELECT phase, phase_since, crisis_depth, recovery_signals, turns_in_phase, updated_at "
            "FROM emotional_arcs WHERE channel_id = $1 AND user_id = $2",
            channel_id,
            user_id,
        )
        if not row:
            return None
        return {
            "phase": row["phase"],
            "phase_since": row["phase_since"],
            "crisis_depth": row["crisis_depth"],
            "recovery_signals": row["recovery_signals"],
            "turns_in_phase": row["turns_in_phase"],
            "updated_at": row["updated_at"],
        }

    async def upsert_arc(
        self,
        channel_id: str,
        user_id: str,
        phase: str,
        phase_since: float,
        crisis_depth: int,
        recovery_signals: int,
        turns_in_phase: int,
    ) -> None:
        try:
            await self._execute(
                "INSERT INTO emotional_arcs (channel_id, user_id, phase, phase_since, "
                "crisis_depth, recovery_signals, turns_in_phase, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
                "ON CONFLICT(channel_id, user_id) DO UPDATE SET phase=excluded.phase, "
                "phase_since=excluded.phase_since, crisis_depth=excluded.crisis_depth, "
                "recovery_signals=excluded.recovery_signals, turns_in_phase=excluded.turns_in_phase, "
                "updated_at=excluded.updated_at",
                channel_id,
                user_id,
                phase,
                phase_since,
                crisis_depth,
                recovery_signals,
                turns_in_phase,
                time.time(),
            )
        except asyncpg.PostgresError as e:
            log.error("arc_upsert_failed", error=str(e))

    # -- Stance log (FIFO, max 20 per channel-user) --

    async def store_stance(
        self,
        channel_id: str,
        user_id: str,
        topic: str,
        position: str,
        confidence: float,
    ) -> None:
        try:
            # Wrap in a transaction so the INSERT + FIFO eviction land
            # atomically — otherwise a crash between the two could leave
            # the table > 20 rows for this (channel, user).
            async with self._tx() as conn:
                await conn.execute(
                    "INSERT INTO stance_log (channel_id, user_id, topic, position, confidence, timestamp) "
                    "VALUES ($1, $2, $3, $4, $5, $6)",
                    channel_id,
                    user_id,
                    topic,
                    position[:200],
                    confidence,
                    time.time(),
                )
                # FIFO eviction: keep max 20 per (channel, user). Without this
                # stance_log grows unbounded for active users and context
                # retrieval starts hitting irrelevant old positions.
                await conn.execute(
                    "DELETE FROM stance_log WHERE channel_id = $1 AND user_id = $2 AND id NOT IN ("
                    "SELECT id FROM stance_log WHERE channel_id = $1 AND user_id = $2 "
                    "ORDER BY timestamp DESC LIMIT 20)",
                    channel_id,
                    user_id,
                )
        except asyncpg.PostgresError as e:
            log.error("stance_store_failed", error=str(e))

    async def get_stances(self, channel_id: str, user_id: str, limit: int = 5) -> list[dict]:
        rows = await self._fetch(
            "SELECT topic, position, confidence, timestamp FROM stance_log "
            "WHERE channel_id = $1 AND user_id = $2 ORDER BY timestamp DESC LIMIT $3",
            channel_id,
            user_id,
            limit,
        )
        return [
            {"topic": r["topic"], "position": r["position"], "confidence": r["confidence"], "timestamp": r["timestamp"]}
            for r in rows
        ]

    # -- Contradictions --

    async def store_contradiction(
        self,
        user_id: str,
        prior: str,
        contradicting: str,
        topic: str,
    ) -> None:
        try:
            await self._execute(
                "INSERT INTO contradiction_log (user_id, prior_statement, contradicting_statement, "
                "topic, called_out, timestamp) VALUES ($1, $2, $3, $4, 0, $5)",
                user_id,
                prior[:300],
                contradicting[:300],
                topic,
                time.time(),
            )
        except asyncpg.PostgresError as e:
            log.error("contradiction_store_failed", error=str(e))
