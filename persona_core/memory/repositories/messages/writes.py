"""Write path of the messages table: idempotent append + pruning.

Every bot reply and user turn lands here; `delete_before` is the only
sanctioned deletion (the table is append-only otherwise).
"""

from __future__ import annotations

import time

import asyncpg
import structlog

from persona_core.memory.base import BaseRepository

log = structlog.get_logger()


class MessagesWrites(BaseRepository):
    """Mutations on the `messages` table (mixed into MessagesRepository)."""

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
        shared context. NULL ids (bot replies, proactive turns) never
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
