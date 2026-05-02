"""Reminders — deferred messages scheduled for a future channel send.

Populated via tool_use (the bot can set a reminder on user request) and
drained by a background loop that polls `get_pending_reminders`. Recurring
reminders are re-scheduled via `update_reminder_time` after delivery."""

from __future__ import annotations

import time

import aiosqlite
import structlog

from insult.core.memory.base import BaseRepository

log = structlog.get_logger()


class RemindersRepository(BaseRepository):
    """Owns the `reminders` table."""

    async def save_reminder(
        self,
        channel_id: str,
        guild_id: str | None,
        created_by: str,
        description: str,
        remind_at: float,
        mention_user_ids: str = "",
        recurring: str = "none",
        requires_ack: bool = False,
    ) -> int:
        """Insert a new reminder. Returns its ID. Raises on DB failure because
        callers need to surface "I couldn't save your reminder" to the user."""
        db = await self._conn()
        try:
            cursor = await db.execute(
                "INSERT INTO reminders (channel_id, guild_id, created_by, description, remind_at, "
                "mention_user_ids, recurring, delivered, created_at, requires_ack) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                (
                    channel_id,
                    guild_id,
                    created_by,
                    description,
                    remind_at,
                    mention_user_ids,
                    recurring,
                    time.time(),
                    1 if requires_ack else 0,
                ),
            )
            await db.commit()
            reminder_id = cursor.lastrowid or 0
            log.info(
                "reminder_saved",
                reminder_id=reminder_id,
                channel_id=channel_id,
                description=description[:80],
                remind_at=remind_at,
                requires_ack=requires_ack,
            )
            return reminder_id
        except aiosqlite.Error as e:
            log.error("reminder_save_failed", channel_id=channel_id, error=str(e))
            raise

    async def get_pending_reminders(self, now: float) -> list[dict]:
        """Reminders that are due (remind_at <= now) and not yet delivered."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT id, channel_id, guild_id, created_by, description, remind_at, "
            "mention_user_ids, recurring, requires_ack FROM reminders "
            "WHERE delivered = 0 AND remind_at <= ? ORDER BY remind_at ASC",
            (now,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "channel_id": r[1],
                "guild_id": r[2],
                "created_by": r[3],
                "description": r[4],
                "remind_at": r[5],
                "mention_user_ids": r[6],
                "recurring": r[7],
                "requires_ack": bool(r[8]) if r[8] is not None else False,
            }
            for r in rows
        ]

    async def mark_reminder_delivered(self, reminder_id: int) -> None:
        db = await self._conn()
        try:
            await db.execute("UPDATE reminders SET delivered = 1 WHERE id = ?", (reminder_id,))
            await db.commit()
        except aiosqlite.Error as e:
            log.error("reminder_mark_delivered_failed", reminder_id=reminder_id, error=str(e))

    async def update_reminder_time(self, reminder_id: int, new_remind_at: float) -> None:
        """For recurring reminders: bump remind_at forward after a delivery."""
        db = await self._conn()
        try:
            await db.execute(
                "UPDATE reminders SET remind_at = ? WHERE id = ?",
                (new_remind_at, reminder_id),
            )
            await db.commit()
        except aiosqlite.Error as e:
            log.error("reminder_update_time_failed", reminder_id=reminder_id, error=str(e))

    async def update_reminder_fields(
        self,
        reminder_id: int,
        *,
        new_remind_at: float | None = None,
        new_description: str | None = None,
    ) -> bool:
        """Patch a not-yet-delivered reminder. Returns True if any field changed.

        Either argument can be None to leave that column untouched. If both
        are None this is a no-op and returns False.
        """
        sets: list[str] = []
        params: list = []
        if new_remind_at is not None:
            sets.append("remind_at = ?")
            params.append(new_remind_at)
        if new_description is not None:
            sets.append("description = ?")
            params.append(new_description)
        if not sets:
            return False
        params.append(reminder_id)
        db = await self._conn()
        try:
            cursor = await db.execute(
                f"UPDATE reminders SET {', '.join(sets)} WHERE id = ? AND delivered = 0",  # noqa: S608
                params,
            )
            await db.commit()
            return cursor.rowcount > 0
        except aiosqlite.Error as e:
            log.error("reminder_update_fields_failed", reminder_id=reminder_id, error=str(e))
            return False

    async def get_channel_reminders(self, channel_id: str) -> list[dict]:
        """All pending (not-yet-delivered) reminders for a channel."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT id, channel_id, guild_id, created_by, description, remind_at, "
            "mention_user_ids, recurring FROM reminders "
            "WHERE channel_id = ? AND delivered = 0 ORDER BY remind_at ASC",
            (channel_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "channel_id": r[1],
                "guild_id": r[2],
                "created_by": r[3],
                "description": r[4],
                "remind_at": r[5],
                "mention_user_ids": r[6],
                "recurring": r[7],
            }
            for r in rows
        ]

    async def set_snooze_msg_id(self, reminder_id: int, msg_id: int) -> None:
        """Tag a reminder with the Discord message id where it was delivered.

        Used by the snooze flow: when a user reacts to that delivered message
        with ⏰/⏭️/📅 we look up the reminder by message id and recreate it
        with a future remind_at."""
        db = await self._conn()
        try:
            await db.execute(
                "UPDATE reminders SET snooze_msg_id = ? WHERE id = ?",
                (msg_id, reminder_id),
            )
            await db.commit()
        except aiosqlite.Error as e:
            log.error("reminder_set_snooze_msg_failed", reminder_id=reminder_id, error=str(e))

    async def get_reminder_for_snooze(self, msg_id: int) -> dict | None:
        """Look up the (delivered) reminder whose snooze_msg_id matches.

        Returns the columns needed to recreate the reminder (channel_id,
        guild_id, created_by, description, mention_user_ids). Returns None
        if no row matches — protects against snooze attempts on stale or
        already-snoozed messages."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT id, channel_id, guild_id, created_by, description, mention_user_ids "
            "FROM reminders WHERE snooze_msg_id = ? LIMIT 1",
            (msg_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "channel_id": row[1],
            "guild_id": row[2],
            "created_by": row[3],
            "description": row[4],
            "mention_user_ids": row[5],
        }

    async def set_ack_metadata(
        self,
        reminder_id: int,
        ack_msg_id: int,
        delivered_at: float,
    ) -> None:
        """Tag a delivered reminder with its ack message id and delivery time.
        Called after a requires_ack reminder is sent so the timeout sweep can
        find rows whose ack window has lapsed."""
        db = await self._conn()
        try:
            await db.execute(
                "UPDATE reminders SET ack_msg_id = ?, delivered_at = ? WHERE id = ?",
                (ack_msg_id, delivered_at, reminder_id),
            )
            await db.commit()
        except aiosqlite.Error as e:
            log.error("reminder_set_ack_metadata_failed", reminder_id=reminder_id, error=str(e))

    async def mark_ack_received(self, ack_msg_id: int) -> bool:
        """Mark a reminder as acknowledged when the user reacts ✅. Returns
        True if a row was updated — False means no reminder matches that
        message id (already acked, expired, or never existed)."""
        db = await self._conn()
        try:
            cursor = await db.execute(
                "UPDATE reminders SET ack_received = 1 WHERE ack_msg_id = ? AND ack_received = 0",
                (ack_msg_id,),
            )
            await db.commit()
            return cursor.rowcount > 0
        except aiosqlite.Error as e:
            log.error("reminder_mark_ack_failed", ack_msg_id=ack_msg_id, error=str(e))
            return False

    async def get_ack_overdue(self, now: float, timeout_seconds: float, max_retries: int) -> list[dict]:
        """Reminders whose ack window has lapsed without a ✅ and that have
        not yet been re-fired (ack_retry_count < max_retries). The returned
        dicts carry the columns needed to enqueue a new pending reminder."""
        db = await self._conn()
        cursor = await db.execute(
            "SELECT id, channel_id, guild_id, created_by, description, mention_user_ids, ack_retry_count "
            "FROM reminders "
            "WHERE requires_ack = 1 AND ack_received = 0 AND delivered = 1 "
            "AND ack_retry_count < ? AND delivered_at IS NOT NULL AND delivered_at <= ?",
            (max_retries, now - timeout_seconds),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "channel_id": r[1],
                "guild_id": r[2],
                "created_by": r[3],
                "description": r[4],
                "mention_user_ids": r[5],
                "ack_retry_count": r[6],
            }
            for r in rows
        ]

    async def increment_ack_retry(self, reminder_id: int) -> None:
        """Bump the retry counter so we don't fire the same overdue ack twice."""
        db = await self._conn()
        try:
            await db.execute(
                "UPDATE reminders SET ack_retry_count = ack_retry_count + 1 WHERE id = ?",
                (reminder_id,),
            )
            await db.commit()
        except aiosqlite.Error as e:
            log.error("reminder_increment_ack_retry_failed", reminder_id=reminder_id, error=str(e))

    async def clear_snooze_msg_id(self, msg_id: int) -> None:
        """Detach the snooze pointer so a second reaction can't double-fire."""
        db = await self._conn()
        try:
            await db.execute(
                "UPDATE reminders SET snooze_msg_id = NULL WHERE snooze_msg_id = ?",
                (msg_id,),
            )
            await db.commit()
        except aiosqlite.Error as e:
            log.error("reminder_clear_snooze_msg_failed", msg_id=msg_id, error=str(e))

    async def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a NOT-yet-delivered reminder. Returns True if a row was removed."""
        db = await self._conn()
        try:
            cursor = await db.execute("DELETE FROM reminders WHERE id = ? AND delivered = 0", (reminder_id,))
            await db.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                log.info("reminder_deleted", reminder_id=reminder_id)
            else:
                log.warning("reminder_delete_not_found", reminder_id=reminder_id)
            return deleted
        except aiosqlite.Error as e:
            log.error("reminder_delete_failed", reminder_id=reminder_id, error=str(e))
            return False
