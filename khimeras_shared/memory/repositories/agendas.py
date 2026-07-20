"""Standing agendas — durable, self-pursued goals a persona works on its own.

The hardest piece of the autonomy dream: a persona (Insult/ALICE/Vultur) that
acts WITHOUT being spoken to. A user asks a persona to keep continuous watch on
something and the persona emits an `[AGENDA:]` marker; a durable row is created
here. A proactive drain loop polls `get_due_agendas` on a cadence, wakes the
persona to pursue the goal (web search + judgment), and posts back only genuine
novelty. Mirrors the `research_jobs` / `reminders` pattern (durable table +
repository + drain loop) already in prod — a standing agenda is a recurring,
self-triggering job rather than a one-shot one.

asyncpg shape (post-2026-05-12 PG migration): `$1, $2, …` placeholders,
INSERT ... RETURNING id for new-row ids."""

from __future__ import annotations

import time

import asyncpg
import structlog

from khimeras_shared.memory.base import BaseRepository

log = structlog.get_logger()


class AgendasRepository(BaseRepository):
    """Owns the `agendas` table."""

    async def save_agenda(
        self,
        persona_id: str | None,
        channel_id: str,
        guild_id: str | None,
        created_by: str,
        goal: str,
        cadence_hours: float = 24,
    ) -> int:
        """Create a new standing agenda. Returns its ID. Raises on DB failure
        because the caller needs to surface "I couldn't set up your watch" to
        the user."""
        try:
            agenda_id = await self._fetchval(
                "INSERT INTO agendas (persona_id, channel_id, guild_id, created_by, "
                "goal, cadence_hours, last_run_at, active, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, NULL, 1, $7) RETURNING id",
                persona_id,
                channel_id,
                guild_id,
                created_by,
                goal,
                cadence_hours,
                time.time(),
            )
            agenda_id = int(agenda_id or 0)
            log.info(
                "agenda_saved",
                agenda_id=agenda_id,
                persona_id=persona_id,
                channel_id=channel_id,
                cadence_hours=cadence_hours,
                goal_preview=goal[:80],
            )
            return agenda_id
        except asyncpg.PostgresError as e:
            log.error("agenda_save_failed", channel_id=channel_id, error=str(e))
            raise

    async def get_due_agendas(self, now: float, limit: int = 3, persona_id: str | None = None) -> list[dict]:
        """Active agendas whose cadence has elapsed, oldest-run first — the
        proactive loop's work batch.

        An agenda is due when it is active and either never ran (`last_run_at`
        is NULL) or its last run is at least `cadence_hours` in the past. When
        `persona_id` is given, only that persona's agendas are returned, so a
        per-persona proactive loop never starves on another persona's agendas
        filling the batch (each sibling bot in the gateway pursues only its own).
        """
        if persona_id is None:
            rows = await self._fetch(
                "SELECT id, persona_id, channel_id, guild_id, created_by, goal, cadence_hours, last_run_at "
                "FROM agendas WHERE active = 1 AND (last_run_at IS NULL OR last_run_at + cadence_hours * 3600 <= $1) "
                "ORDER BY last_run_at ASC NULLS FIRST LIMIT $2",
                now,
                limit,
            )
        else:
            rows = await self._fetch(
                "SELECT id, persona_id, channel_id, guild_id, created_by, goal, cadence_hours, last_run_at "
                "FROM agendas WHERE active = 1 AND persona_id = $3 "
                "AND (last_run_at IS NULL OR last_run_at + cadence_hours * 3600 <= $1) "
                "ORDER BY last_run_at ASC NULLS FIRST LIMIT $2",
                now,
                limit,
                persona_id,
            )
        return [
            {
                "id": r["id"],
                "persona_id": r["persona_id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "goal": r["goal"],
                "cadence_hours": r["cadence_hours"],
                "last_run_at": r["last_run_at"],
            }
            for r in rows
        ]

    async def mark_agenda_ran(self, agenda_id: int, now: float) -> None:
        """Stamp the last-run time so the cadence gate holds until the next
        window. Log-and-swallow: a lost stamp just re-runs the agenda one cadence
        early, so it must never crash the proactive loop."""
        try:
            await self._execute("UPDATE agendas SET last_run_at = $1 WHERE id = $2", now, agenda_id)
        except asyncpg.PostgresError as e:
            log.error("agenda_mark_ran_failed", agenda_id=agenda_id, error=str(e))

    async def deactivate_agenda(self, agenda_id: int) -> None:
        """Retire a standing agenda (user asked to stop, or it's exhausted).
        Log-and-swallow — a failed deactivate just leaves it running one more
        cadence, never a crash."""
        try:
            await self._execute("UPDATE agendas SET active = 0 WHERE id = $1", agenda_id)
        except asyncpg.PostgresError as e:
            log.error("agenda_deactivate_failed", agenda_id=agenda_id, error=str(e))

    async def get_channel_agendas(self, channel_id: str) -> list[dict]:
        """All active standing agendas for a channel — used to show the user
        what a persona is currently watching for them."""
        rows = await self._fetch(
            "SELECT id, persona_id, channel_id, guild_id, created_by, goal, cadence_hours, last_run_at "
            "FROM agendas WHERE channel_id = $1 AND active = 1 ORDER BY created_at ASC",
            channel_id,
        )
        return [
            {
                "id": r["id"],
                "persona_id": r["persona_id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "goal": r["goal"],
                "cadence_hours": r["cadence_hours"],
                "last_run_at": r["last_run_at"],
            }
            for r in rows
        ]
