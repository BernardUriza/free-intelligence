"""Messages table — conversational store, context retrieval, keyword search.

This is the hot path: every user turn reads recent + relevant, and every
bot reply writes a new row. Also sources the channel-awareness helpers
(participants, activity) because they query the same table. The messages
table is append-only except for explicit pruning via `delete_before`.

Migrated to asyncpg on 2026-05-12 PG migration. Placeholders `?` → `$N`,
`aiosqlite.Error` → `asyncpg.PostgresError`. The connection pool removes
the SQLite single-writer bottleneck — recent + search + participants can
run concurrently on different conns.
"""

from __future__ import annotations

import time

import asyncpg
import structlog

from khimeras_shared.memory.base import BaseRepository

log = structlog.get_logger()


class MessagesRepository(BaseRepository):
    """Owns the `messages` table plus every read of it (participants, activity)."""

    # -- Writes --

    async def store(
        self,
        channel_id: str,
        user_id: str,
        user_name: str,
        role: str,
        content: str,
        for_user_id: str | None = None,
        guild_id: str | None = None,
        channel_name: str | None = None,
        model_used: str | None = None,
        discord_message_id: str | None = None,
    ) -> None:
        """Append a message. Raises asyncpg.PostgresError on failure so the caller
        can decide whether to log-and-continue or bail.

        ``discord_message_id`` makes the write idempotent: the Insult plumbing
        and every persona_gateway sibling each receive the same Discord message
        on their own gateway connection, and whichever stores it first wins —
        the second insert is a no-op instead of a duplicate row poisoning the
        shared context. NULL ids (bot replies, proactive, moltbook) never
        conflict."""
        try:
            tag = await self._execute(
                "INSERT INTO messages (channel_id, user_id, user_name, role, content, timestamp, "
                "for_user_id, guild_id, channel_name, model_used, discord_message_id) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) "
                "ON CONFLICT (discord_message_id) WHERE discord_message_id IS NOT NULL DO NOTHING",
                channel_id,
                user_id,
                user_name,
                role,
                content,
                time.time(),
                for_user_id,
                guild_id,
                channel_name,
                model_used,
                discord_message_id,
            )
            if tag == "INSERT 0 0":
                log.info(
                    "memory_store_deduped",
                    channel_id=channel_id,
                    user_id=user_id,
                    discord_message_id=discord_message_id,
                )
        except asyncpg.PostgresError as e:
            log.error("memory_store_failed", channel_id=channel_id, user_id=user_id, error=str(e))
            raise

    async def append_content_by_discord_id(self, discord_message_id: str, suffix: str) -> bool:
        """Append text to an already-stored row, keyed by its Discord message id.

        Powers the image-transcript trace: the row is stored synchronously at
        intake (empty content for an image-only message) and the vision
        transcript arrives seconds later from a background task. Keying on
        discord_message_id means the append lands no matter which writer won
        the deduped insert. Returns True when a row was updated."""
        try:
            tag = await self._execute(
                "UPDATE messages SET content = CASE WHEN content = '' THEN $2 "
                "ELSE content || E'\\n' || $2 END "
                "WHERE discord_message_id = $1",
                discord_message_id,
                suffix,
            )
        except asyncpg.PostgresError as e:
            log.error(
                "memory_append_failed",
                discord_message_id=discord_message_id,
                error=str(e),
            )
            raise
        return tag == "UPDATE 1"

    async def delete_before(self, cutoff: float) -> int:
        """Delete messages older than cutoff timestamp. Returns count deleted."""
        count = await self._fetchval("SELECT COUNT(*) FROM messages WHERE timestamp < $1", cutoff)
        count = count or 0
        if count > 0:
            await self._execute("DELETE FROM messages WHERE timestamp < $1", cutoff)
            log.info("memory_cleaned", deleted=count, cutoff=cutoff)
        return count

    async def count_before(self, cutoff: float) -> int:
        """Read-only sibling of `delete_before` for dry-run CLIs (`db-clean --dry-run`)."""
        return int(await self._fetchval("SELECT COUNT(*) FROM messages WHERE timestamp < $1", cutoff) or 0)

    async def count_messages_for_user(self, user_id: str) -> int:
        """Total messages stored for a user (across channels). Useful for tests
        that want to assert side-effects without parsing the full message list."""
        return int(
            await self._fetchval(
                "SELECT COUNT(*) FROM messages WHERE user_id = $1",
                user_id,
            )
            or 0
        )

    async def get_latest_username_per_user(self) -> dict[str, str]:
        """Map user_id → most recent user_name from the messages table.

        Used by the dream-diary CLI to show readable names instead of Discord
        snowflakes. Indexed scan, dirt-cheap; only `role = 'user'` rows so we
        never resolve the bot's own user_id to "Insult"."""
        rows = await self._fetch(
            "SELECT DISTINCT ON (user_id) user_id, user_name FROM messages "
            "WHERE role = 'user' ORDER BY user_id, id DESC"
        )
        return {r["user_id"]: r["user_name"] for r in rows}

    # -- Reads: per-channel and per-user history --

    async def get_recent(self, channel_id: str, limit: int = 20, user_id: str | None = None) -> list[dict]:
        """Last N messages, optionally filtered by user.

        When user_id is provided, returns messages sent BY the user plus
        assistant replies addressed TO the user (for_user_id match) so
        per-user context isolation is possible in shared channels.

        Each row carries `user_id` AND `user_name`. The user_id was added
        in v3.7.25 because the OUTBOUND lane needs distinct user identities
        to run the vulnerability gate against — pulling user_id by name
        was racy when two users happened to share a display name across
        guilds.
        """
        if user_id:
            rows = await self._fetch(
                "SELECT user_id, user_name, role, content, timestamp FROM messages "
                "WHERE channel_id = $1 AND (user_id = $2 OR for_user_id = $2) "
                "ORDER BY timestamp DESC LIMIT $3",
                channel_id,
                user_id,
                limit,
            )
        else:
            rows = await self._fetch(
                "SELECT user_id, user_name, role, content, timestamp FROM messages "
                "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
                channel_id,
                limit,
            )
        return [
            {
                "user_id": r["user_id"],
                "user_name": r["user_name"],
                "role": r["role"],
                "content": r["content"],
                "timestamp": r["timestamp"],
            }
            for r in reversed(rows)
        ]

    async def search(self, channel_id: str, query: str, limit: int = 5, user_id: str | None = None) -> list[dict]:
        """Keyword ILIKE-search across message content, optionally scoped to a user.

        Words <=2 chars are dropped to avoid OR-exploding into every row.
        Uses ILIKE (case-insensitive) — Postgres equivalent of SQLite's
        default-collation LIKE. No FTS here — this is the cheap fallback
        path; the semantic search path lives in `FactsRepository.search_facts_semantic`.
        """
        words = [f"%{w}%" for w in query.split() if len(w) > 2]
        if not words:
            return []

        # Build $N placeholders for the OR-list, starting after the fixed args.
        if user_id:
            fixed = [channel_id, user_id]
            offset = len(fixed) + 1
            conditions = " OR ".join(f"content ILIKE ${offset + i}" for i in range(len(words)))
            sql = (
                f"SELECT user_name, role, content, timestamp FROM messages "  # noqa: S608
                f"WHERE channel_id = $1 AND (user_id = $2 OR for_user_id = $2) AND ({conditions}) "
                f"ORDER BY timestamp DESC LIMIT ${offset + len(words)}"
            )
            rows = await self._fetch(sql, *fixed, *words, limit)
        else:
            fixed = [channel_id]
            offset = len(fixed) + 1
            conditions = " OR ".join(f"content ILIKE ${offset + i}" for i in range(len(words)))
            sql = (
                f"SELECT user_name, role, content, timestamp FROM messages "  # noqa: S608
                f"WHERE channel_id = $1 AND ({conditions}) "
                f"ORDER BY timestamp DESC LIMIT ${offset + len(words)}"
            )
            rows = await self._fetch(sql, *fixed, *words, limit)
        return [
            {"user_name": r["user_name"], "role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in reversed(rows)
        ]

    async def get_all_user_messages(self, limit_per_user: int = 30) -> dict[str, dict]:
        """Recent messages grouped by user_id (cross-channel).

        Used by bulk fact-extraction and the debug dashboard. Returns a dict
        keyed by user_id with `{user_name, messages: [...]}` — not a flat list,
        because callers always need to group by user anyway."""
        users = await self._fetch(
            "SELECT DISTINCT user_id, user_name FROM messages WHERE role = 'user' ORDER BY user_id"
        )

        result: dict[str, dict] = {}
        for u in users:
            user_id = u["user_id"]
            user_name = u["user_name"]
            rows = await self._fetch(
                "SELECT user_name, role, content, timestamp FROM messages "
                "WHERE user_id = $1 OR for_user_id = $1 ORDER BY timestamp DESC LIMIT $2",
                user_id,
                limit_per_user,
            )
            result[user_id] = {
                "user_name": user_name,
                "messages": [
                    {
                        "user_name": r["user_name"],
                        "role": r["role"],
                        "content": r["content"],
                        "timestamp": r["timestamp"],
                    }
                    for r in reversed(rows)
                ],
            }
        return result

    async def get_recent_for_summary(self, channel_id: str, limit: int = 50) -> list[dict]:
        """Recent messages for the channel-summarization background task.

        Same projection as `get_recent` but without user filtering — summaries
        are channel-wide by design."""
        rows = await self._fetch(
            "SELECT user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
            channel_id,
            limit,
        )
        return [
            {"user_name": r["user_name"], "role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in reversed(rows)
        ]

    # -- Reads: aggregates over the messages table --

    async def get_stats(self, channel_id: str | None = None) -> dict:
        """Row counts for health checks and the /debug/stats endpoint."""
        if channel_id:
            row = await self._fetchrow(
                "SELECT COUNT(*) AS total, COUNT(DISTINCT user_id) AS users FROM messages WHERE channel_id = $1",
                channel_id,
            )
            if not row:
                return {"total_messages": 0, "unique_users": 0, "unique_channels": None}
            return {
                "total_messages": row["total"],
                "unique_users": row["users"],
                "unique_channels": None,
            }
        row = await self._fetchrow(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT user_id) AS users, "
            "COUNT(DISTINCT channel_id) AS channels FROM messages"
        )
        if not row:
            return {"total_messages": 0, "unique_users": 0, "unique_channels": 0}
        return {
            "total_messages": row["total"],
            "unique_users": row["users"],
            "unique_channels": row["channels"],
        }

    async def get_channel_participants(self, channel_id: str, limit: int = 10) -> list[dict]:
        """Distinct users who posted in a channel, most recent first.

        Used by chat.py to inject other-participants facts into the prompt
        (group-chat awareness)."""
        rows = await self._fetch(
            "SELECT user_id, user_name, MAX(timestamp) AS last_ts FROM messages "
            "WHERE channel_id = $1 AND role = 'user' "
            "GROUP BY user_id, user_name ORDER BY last_ts DESC LIMIT $2",
            channel_id,
            limit,
        )
        return [{"user_id": r["user_id"], "user_name": r["user_name"], "last_ts": r["last_ts"]} for r in rows]

    async def get_channel_activity_since(self, guild_id: str, since_ts: float) -> list[dict]:
        """(channel_id, count) pairs for channels with activity since a timestamp."""
        rows = await self._fetch(
            "SELECT channel_id, COUNT(*) AS cnt FROM messages "
            "WHERE guild_id = $1 AND timestamp > $2 "
            "GROUP BY channel_id ORDER BY cnt DESC",
            guild_id,
            since_ts,
        )
        return [{"channel_id": r["channel_id"], "count": r["cnt"]} for r in rows]

    async def get_channels_overview(self, limit: int = 50) -> list[dict]:
        """All channels with message counts and latest timestamp. Debug helper."""
        rows = await self._fetch(
            "SELECT channel_id, MAX(channel_name) AS channel_name, MAX(guild_id) AS guild_id, "
            "COUNT(*) AS cnt, MAX(timestamp) AS last_ts "
            "FROM messages GROUP BY channel_id ORDER BY MAX(timestamp) DESC LIMIT $1",
            limit,
        )
        return [
            {
                "channel_id": r["channel_id"],
                "channel_name": r["channel_name"],
                "guild_id": r["guild_id"],
                "count": r["cnt"],
                "last_ts": r["last_ts"],
            }
            for r in rows
        ]
