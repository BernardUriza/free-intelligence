"""Aggregate reads over the messages table: stats, counts, channel awareness.

These queries never return message content — only counts, participants and
activity shapes for health checks, debug surfaces and group-chat context.
"""

from __future__ import annotations

from khimeras_shared.memory.base import BaseRepository


class MessagesAggregates(BaseRepository):
    """Aggregations (mixed into MessagesRepository)."""

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
