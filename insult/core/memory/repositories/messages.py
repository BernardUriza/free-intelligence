"""Messages table — conversational store, context retrieval, keyword search.

This is the hot path: every user turn reads recent + relevant, and every
bot reply writes a new row. Also sources the channel-awareness helpers
(participants, activity) because they query the same table. The messages
table is append-only except for explicit pruning via `delete_before`.
"""

from __future__ import annotations

import time

import aiosqlite
import structlog

from insult.core.memory.base import BaseRepository

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
    ) -> None:
        """Append a message. Raises aiosqlite.Error on failure so the caller
        can decide whether to log-and-continue or bail."""
        db = await self._conn()
        try:
            await db.execute(
                "INSERT INTO messages (channel_id, user_id, user_name, role, content, timestamp, for_user_id, guild_id, channel_name, model_used) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
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
                ),
            )
            await db.commit()
        except aiosqlite.Error as e:
            log.error("memory_store_failed", channel_id=channel_id, user_id=user_id, error=str(e))
            raise

    async def delete_before(self, cutoff: float) -> int:
        """Delete messages older than cutoff timestamp. Returns count deleted."""
        db = await self._conn()
        cursor = await db.execute("SELECT COUNT(*) FROM messages WHERE timestamp < ?", (cutoff,))
        row = await cursor.fetchone()
        count = row[0] if row else 0
        if count > 0:
            await db.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
            await db.commit()
            log.info("memory_cleaned", deleted=count, cutoff=cutoff)
        return count

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
        db = await self._conn()
        if user_id:
            cursor = await db.execute(
                "SELECT user_id, user_name, role, content, timestamp FROM messages "
                "WHERE channel_id = ? AND (user_id = ? OR for_user_id = ?) "
                "ORDER BY timestamp DESC LIMIT ?",
                (channel_id, user_id, user_id, limit),
            )
        else:
            cursor = await db.execute(
                "SELECT user_id, user_name, role, content, timestamp FROM messages "
                "WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?",
                (channel_id, limit),
            )
        rows = await cursor.fetchall()
        return [
            {"user_id": r[0], "user_name": r[1], "role": r[2], "content": r[3], "timestamp": r[4]}
            for r in reversed(rows)
        ]

    async def search(self, channel_id: str, query: str, limit: int = 5, user_id: str | None = None) -> list[dict]:
        """Keyword LIKE-search across message content, optionally scoped to a user.

        Words <=2 chars are dropped to avoid OR-exploding into every row.
        No FTS here — this is the cheap fallback path; the semantic search
        path lives in `FactsRepository.search_facts_semantic`.
        """
        db = await self._conn()
        words = [f"%{w}%" for w in query.split() if len(w) > 2]
        if not words:
            return []

        conditions = " OR ".join(["content LIKE ?"] * len(words))
        if user_id:
            cursor = await db.execute(
                f"SELECT user_name, role, content, timestamp FROM messages "  # noqa: S608
                f"WHERE channel_id = ? AND (user_id = ? OR for_user_id = ?) AND ({conditions}) "
                f"ORDER BY timestamp DESC LIMIT ?",
                (channel_id, user_id, user_id, *words, limit),
            )
        else:
            cursor = await db.execute(
                f"SELECT user_name, role, content, timestamp FROM messages "  # noqa: S608
                f"WHERE channel_id = ? AND ({conditions}) "
                f"ORDER BY timestamp DESC LIMIT ?",
                (channel_id, *words, limit),
            )
        rows = await cursor.fetchall()
        return [{"user_name": r[0], "role": r[1], "content": r[2], "timestamp": r[3]} for r in reversed(rows)]

    async def get_all_user_messages(self, limit_per_user: int = 30) -> dict[str, dict]:
        """Recent messages grouped by user_id (cross-channel).

        Used by bulk fact-extraction and the debug dashboard. Returns a dict
        keyed by user_id with `{user_name, messages: [...]}` — not a flat list,
        because callers always need to group by user anyway."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT DISTINCT user_id, user_name FROM messages WHERE role = 'user' ORDER BY timestamp DESC"
        )
        users = await cursor.fetchall()

        result: dict[str, dict] = {}
        for user_id, user_name in users:
            cursor = await db.execute(
                "SELECT user_name, role, content, timestamp FROM messages "
                "WHERE user_id = ? OR for_user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, user_id, limit_per_user),
            )
            rows = await cursor.fetchall()
            result[user_id] = {
                "user_name": user_name,
                "messages": [
                    {"user_name": r[0], "role": r[1], "content": r[2], "timestamp": r[3]} for r in reversed(rows)
                ],
            }
        return result

    async def get_recent_for_summary(self, channel_id: str, limit: int = 50) -> list[dict]:
        """Recent messages for the channel-summarization background task.

        Same projection as `get_recent` but without user filtering — summaries
        are channel-wide by design."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = ? ORDER BY timestamp DESC LIMIT ?",
            (channel_id, limit),
        )
        rows = await cursor.fetchall()
        return [{"user_name": r[0], "role": r[1], "content": r[2], "timestamp": r[3]} for r in reversed(rows)]

    # -- Reads: aggregates over the messages table --

    async def get_stats(self, channel_id: str | None = None) -> dict:
        """Row counts for health checks and the /debug/stats endpoint."""
        db = await self._conn()
        if channel_id:
            cursor = await db.execute(
                "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM messages WHERE channel_id = ?",
                (channel_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT COUNT(*), COUNT(DISTINCT user_id), COUNT(DISTINCT channel_id) FROM messages"
            )
        row = await cursor.fetchone()
        if not row:
            return {"total_messages": 0, "unique_users": 0, "unique_channels": None}
        return {
            "total_messages": row[0],
            "unique_users": row[1],
            "unique_channels": row[2] if len(row) > 2 else None,
        }

    async def get_channel_participants(self, channel_id: str, limit: int = 10) -> list[dict]:
        """Distinct users who posted in a channel, most recent first.

        Used by chat.py to inject other-participants facts into the prompt
        (group-chat awareness)."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT user_id, user_name, MAX(timestamp) as last_ts FROM messages "
            "WHERE channel_id = ? AND role = 'user' "
            "GROUP BY user_id ORDER BY last_ts DESC LIMIT ?",
            (channel_id, limit),
        )
        rows = await cursor.fetchall()
        return [{"user_id": r[0], "user_name": r[1], "last_ts": r[2]} for r in rows]

    async def get_channel_activity_since(self, guild_id: str, since_ts: float) -> list[dict]:
        """(channel_id, count) pairs for channels with activity since a timestamp."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT channel_id, COUNT(*) as cnt FROM messages "
            "WHERE guild_id = ? AND timestamp > ? "
            "GROUP BY channel_id ORDER BY cnt DESC",
            (guild_id, since_ts),
        )
        rows = await cursor.fetchall()
        return [{"channel_id": r[0], "count": r[1]} for r in rows]

    async def get_channels_overview(self, limit: int = 50) -> list[dict]:
        """All channels with message counts and latest timestamp. Debug helper."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT channel_id, MAX(channel_name), MAX(guild_id), COUNT(*), MAX(timestamp) "
            "FROM messages GROUP BY channel_id ORDER BY MAX(timestamp) DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "channel_id": r[0],
                "channel_name": r[1],
                "guild_id": r[2],
                "count": r[3],
                "last_ts": r[4],
            }
            for r in rows
        ]
