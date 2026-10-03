"""Research jobs — durable cross-turn deep-research work queued for a worker.

A persona (Insult/ALICE) acknowledges a heavy research request in-band and
emits a `[RESEARCH:]` marker; a background drain loop pulls `get_pending_jobs`,
runs the job, and posts the result back to the originating channel. Mirrors the
`reminders` pattern (durable table + repository + drain loop) already in prod.

asyncpg shape (post-2026-05-12 PG migration): `$1, $2, …` placeholders,
INSERT ... RETURNING id for new-row ids, and `_affected_rows` to read the
command tag for UPDATE row counts."""

from __future__ import annotations

import time

import asyncpg
import structlog

from persona_core.memory.base import BaseRepository
from persona_core.memory.repositories.reminders import _affected_rows

log = structlog.get_logger()


class ResearchJobsRepository(BaseRepository):
    """Owns the `research_jobs` table."""

    async def save_job(
        self,
        channel_id: str,
        guild_id: str | None,
        created_by: str,
        prompt: str,
        persona_id: str | None = None,
    ) -> int:
        """Queue a new research job. Returns its ID. Raises on DB failure because
        the caller needs to surface "I couldn't queue your research" to the user."""
        try:
            job_id = await self._fetchval(
                "INSERT INTO research_jobs (channel_id, guild_id, created_by, persona_id, "
                "prompt, status, retry_count, created_at) "
                "VALUES ($1, $2, $3, $4, $5, 'queued', 0, $6) RETURNING id",
                channel_id,
                guild_id,
                created_by,
                persona_id,
                prompt,
                time.time(),
            )
            job_id = int(job_id or 0)
            log.info(
                "research_job_saved",
                job_id=job_id,
                channel_id=channel_id,
                persona_id=persona_id,
                prompt_preview=prompt[:80],
            )
            return job_id
        except asyncpg.PostgresError as e:
            log.error("research_job_save_failed", channel_id=channel_id, error=str(e))
            raise

    async def get_pending_jobs(self, limit: int = 3, persona_id: str | None = None) -> list[dict]:
        """Queued jobs, oldest first, up to `limit` — the drain loop's work batch.

        When `persona_id` is given, only that persona's jobs are returned, so a
        per-persona drain loop never starves on another persona's jobs filling the
        batch (each sibling bot in the gateway drains only its own)."""
        if persona_id is None:
            rows = await self._fetch(
                "SELECT id, channel_id, guild_id, created_by, persona_id, prompt, retry_count "
                "FROM research_jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT $1",
                limit,
            )
        else:
            rows = await self._fetch(
                "SELECT id, channel_id, guild_id, created_by, persona_id, prompt, retry_count "
                "FROM research_jobs WHERE status = 'queued' AND persona_id = $2 ORDER BY created_at ASC LIMIT $1",
                limit,
                persona_id,
            )
        return [
            {
                "id": r["id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "persona_id": r["persona_id"],
                "prompt": r["prompt"],
                "retry_count": r["retry_count"],
            }
            for r in rows
        ]

    async def mark_running(self, job_id: int) -> None:
        """Claim a job for a worker. Log-and-swallow: a lost claim is recovered
        by `reset_stale_running`, so it must never crash the drain loop."""
        try:
            await self._execute("UPDATE research_jobs SET status = 'running' WHERE id = $1", job_id)
        except asyncpg.PostgresError as e:
            log.error("research_job_mark_running_failed", job_id=job_id, error=str(e))

    async def mark_done(self, job_id: int, result: str) -> None:
        """Record the finished result and delivery time. Log-and-swallow."""
        try:
            await self._execute(
                "UPDATE research_jobs SET status = 'done', result = $1, delivered_at = $2 WHERE id = $3",
                result,
                time.time(),
                job_id,
            )
        except asyncpg.PostgresError as e:
            log.error("research_job_mark_done_failed", job_id=job_id, error=str(e))

    async def mark_failed(self, job_id: int) -> None:
        """Mark a job dead after its retries are exhausted. Log-and-swallow."""
        try:
            await self._execute(
                "UPDATE research_jobs SET status = 'failed', retry_count = retry_count + 1 WHERE id = $1",
                job_id,
            )
        except asyncpg.PostgresError as e:
            log.error("research_job_mark_failed_failed", job_id=job_id, error=str(e))

    async def requeue(self, job_id: int) -> None:
        """Return a job to the queue for another attempt, bumping the retry
        counter so a poison job doesn't loop forever. Log-and-swallow."""
        try:
            await self._execute(
                "UPDATE research_jobs SET status = 'queued', retry_count = retry_count + 1 WHERE id = $1",
                job_id,
            )
        except asyncpg.PostgresError as e:
            log.error("research_job_requeue_failed", job_id=job_id, error=str(e))

    async def reset_stale_running(self, older_than_s: float) -> int:
        """Requeue jobs stuck in 'running' past `older_than_s` — recovers work
        orphaned when a worker crashed mid-job. Returns the number recovered."""
        try:
            tag = await self._execute(
                "UPDATE research_jobs SET status = 'queued' WHERE status = 'running' AND created_at < $1",
                time.time() - older_than_s,
            )
            recovered = _affected_rows(tag)
            if recovered:
                log.info("research_job_reset_stale_running", recovered=recovered, older_than_s=older_than_s)
            return recovered
        except asyncpg.PostgresError as e:
            log.error("research_job_reset_stale_failed", error=str(e))
            return 0
