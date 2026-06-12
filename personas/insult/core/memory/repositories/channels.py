"""Channel summaries — cross-channel awareness via pre-aggregated digests.

Populated by a background summarization task. Read during prompt building
to give Insult a "server pulse" (what's happening in other channels)
without shipping every channel's transcript into context.

Migrated to asyncpg on 2026-05-12 PG migration."""

from __future__ import annotations

import time

import asyncpg
import structlog

from personas.insult.core.memory.base import BaseRepository

log = structlog.get_logger()


class ChannelSummariesRepository(BaseRepository):
    """Owns the `channel_summaries` table."""

    async def upsert_channel_summary(
        self,
        guild_id: str,
        channel_id: str,
        channel_name: str,
        summary: str,
        message_count: int,
        last_message_ts: float,
        is_private: bool = False,
    ) -> None:
        """Insert or overwrite the summary for a (guild, channel) pair."""
        try:
            await self._execute(
                "INSERT INTO channel_summaries (guild_id, channel_id, channel_name, summary, "
                "message_count, last_message_ts, is_private, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) "
                "ON CONFLICT(guild_id, channel_id) DO UPDATE SET "
                "channel_name=excluded.channel_name, summary=excluded.summary, "
                "message_count=excluded.message_count, last_message_ts=excluded.last_message_ts, "
                "is_private=excluded.is_private, updated_at=excluded.updated_at",
                guild_id,
                channel_id,
                channel_name,
                summary,
                message_count,
                last_message_ts,
                int(is_private),
                time.time(),
            )
            log.info(
                "channel_summary_upserted",
                guild_id=guild_id,
                channel_id=channel_id,
                channel_name=channel_name,
            )
        except asyncpg.PostgresError as e:
            log.error("channel_summary_upsert_failed", channel_id=channel_id, error=str(e))

    async def get_channel_summaries(
        self,
        guild_id: str,
        exclude_channel_id: str | None = None,
        limit: int = 8,
    ) -> list[dict]:
        """Summaries for the server-pulse prompt block.

        `exclude_channel_id` is typically the channel Insult is currently
        replying in — we don't want to echo that channel's own summary back
        at it as "cross-channel awareness"."""
        if exclude_channel_id:
            rows = await self._fetch(
                "SELECT channel_id, channel_name, summary, message_count, last_message_ts, "
                "is_private, updated_at FROM channel_summaries "
                "WHERE guild_id = $1 AND channel_id != $2 "
                "ORDER BY updated_at DESC LIMIT $3",
                guild_id,
                exclude_channel_id,
                limit,
            )
        else:
            rows = await self._fetch(
                "SELECT channel_id, channel_name, summary, message_count, last_message_ts, "
                "is_private, updated_at FROM channel_summaries "
                "WHERE guild_id = $1 ORDER BY updated_at DESC LIMIT $2",
                guild_id,
                limit,
            )
        return [
            {
                "channel_id": r["channel_id"],
                "channel_name": r["channel_name"],
                "summary": r["summary"],
                "message_count": r["message_count"],
                "last_message_ts": r["last_message_ts"],
                "is_private": bool(r["is_private"]),
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
