"""History reads of the messages table: recent context, keyword search,
per-user bulk pulls and the summarization projection.

This is the read side of the hot path — every turn builds its context here.
"""

from __future__ import annotations

from persona_core.memory.base import BaseRepository
from persona_core.memory.repositories.messages.stopwords import search_terms


class MessagesHistory(BaseRepository):
    """Conversational reads (mixed into MessagesRepository)."""

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
                "SELECT user_id, user_name, role, content, timestamp, reactions FROM messages "
                "WHERE channel_id = $1 AND (user_id = $2 OR for_user_id = $2) "
                "ORDER BY timestamp DESC LIMIT $3",
                channel_id,
                user_id,
                limit,
            )
        else:
            rows = await self._fetch(
                "SELECT user_id, user_name, role, content, timestamp, reactions FROM messages "
                "WHERE channel_id = $1 ORDER BY timestamp DESC LIMIT $2",
                channel_id,
                limit,
            )
        # `reactions` rides every row (the persona's gesture on its own turn,
        # v4.47.0) so the framer can say a reaction-only turn WAS an answer.
        return [
            {
                "user_id": r["user_id"],
                "user_name": r["user_name"],
                "role": r["role"],
                "content": r["content"],
                "timestamp": r["timestamp"],
                "reactions": list(r["reactions"] or []),
            }
            for r in reversed(rows)
        ]

    async def recent_assistant_turns(self, user_name: str, limit: int = 40) -> list[dict]:
        """Last N turns THIS persona spoke, across every channel, oldest first.

        The reflection loop's raw material: what the persona actually said this
        week is the only honest source for "what tastes did I confirm?". Keyed
        by display name because assistant rows share bot-ish user_ids across
        hosts, while `user_name` is the persona's stable display name."""
        rows = await self._fetch(
            # A reaction-only turn (content '') is not something the persona
            # SAID; the reflection loop only reads words. A probe's reply is
            # synthetic traffic, not a taste the persona confirmed (v4.47.1).
            "SELECT channel_id, content, timestamp FROM messages "
            "WHERE role = 'assistant' AND user_name = $1 AND content <> '' "
            "AND origin IS DISTINCT FROM 'probe' "
            "ORDER BY timestamp DESC LIMIT $2",
            user_name,
            limit,
        )
        return [
            {"channel_id": r["channel_id"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in reversed(rows)
        ]

    async def search(self, channel_id: str, query: str, limit: int = 5, user_id: str | None = None) -> list[dict]:
        """Keyword ILIKE-search across message content, optionally scoped to a user.

        Uses ILIKE (case-insensitive) — Postgres equivalent of SQLite's
        default-collation LIKE. No FTS here — this is the cheap fallback
        path; the semantic search path lives in `FactsRepository.search_facts_semantic`.
        """
        words = [f"%{w}%" for w in search_terms(query)]
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
