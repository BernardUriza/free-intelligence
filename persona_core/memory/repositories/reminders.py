"""Reminders — deferred messages scheduled for a future channel send.

Populated via tool_use (the bot can set a reminder on user request) and
drained by a background loop that polls `get_pending_reminders`. Recurring
reminders are re-scheduled via `update_reminder_time` after delivery.

Migrated to asyncpg on 2026-05-12 PG migration. `cursor.lastrowid` is
not a thing in asyncpg — INSERT uses RETURNING id. `cursor.rowcount`
becomes the command-tag parse from `_execute` for UPDATEs/DELETEs."""

from __future__ import annotations

import time

import asyncpg
import structlog

from persona_core.memory.base import BaseRepository

log = structlog.get_logger()


_CRITERION_QUOTE_CHARS = "\u00ab\u00bb\"'\u201c\u201d\u2018\u2019"


def _affected_rows(command_tag: str) -> int:
    """Parse asyncpg's command tag (e.g. 'UPDATE 3', 'DELETE 1') into an int.

    asyncpg's pool.execute returns a string of the form `<VERB> [<oid>] <count>`.
    For our INSERT/UPDATE/DELETE statements the count is the trailing token
    — same value SQLite's `cursor.rowcount` returned."""
    try:
        return int(command_tag.rsplit(" ", 1)[-1])
    except ValueError, AttributeError:
        return 0


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
        persona_id: str | None = None,
    ) -> int:
        """Insert a new reminder. Returns its ID. Raises on DB failure because
        callers need to surface "I couldn't save your reminder" to the user."""
        try:
            reminder_id = await self._fetchval(
                "INSERT INTO reminders (channel_id, guild_id, created_by, description, remind_at, "
                "mention_user_ids, recurring, delivered, created_at, requires_ack, persona_id) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, 0, $8, $9, $10) RETURNING id",
                channel_id,
                guild_id,
                created_by,
                description,
                remind_at,
                mention_user_ids,
                recurring,
                time.time(),
                1 if requires_ack else 0,
                persona_id,
            )
            reminder_id = int(reminder_id or 0)
            log.info(
                "reminder_saved",
                reminder_id=reminder_id,
                channel_id=channel_id,
                persona_id=persona_id,
                description=description[:80],
                remind_at=remind_at,
                requires_ack=requires_ack,
            )
            return reminder_id
        except asyncpg.PostgresError as e:
            log.error("reminder_save_failed", channel_id=channel_id, error=str(e))
            raise

    async def get_pending_reminders(self, now: float, persona_id: str | None = None) -> list[dict]:
        """Reminders that are due (remind_at <= now) and not yet delivered.

        When `persona_id` is given, only THAT persona's rows are returned — the
        same ownership contract as `research_jobs`/`agendas`: every persona-bot
        drains its own queue, so Vultur never delivers what Insult agendó (and a
        reminder is never delivered N times, once per live persona-bot).
        """
        if persona_id is None:
            rows = await self._fetch(
                "SELECT id, channel_id, guild_id, created_by, description, remind_at, "
                "mention_user_ids, recurring, requires_ack, persona_id FROM reminders "
                "WHERE delivered = 0 AND remind_at <= $1 ORDER BY remind_at ASC",
                now,
            )
        else:
            rows = await self._fetch(
                "SELECT id, channel_id, guild_id, created_by, description, remind_at, "
                "mention_user_ids, recurring, requires_ack, persona_id FROM reminders "
                "WHERE delivered = 0 AND remind_at <= $1 AND persona_id = $2 ORDER BY remind_at ASC",
                now,
                persona_id,
            )
        return [
            {
                "id": r["id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "description": r["description"],
                "remind_at": r["remind_at"],
                "mention_user_ids": r["mention_user_ids"],
                "recurring": r["recurring"],
                "requires_ack": bool(r["requires_ack"]) if r["requires_ack"] is not None else False,
                "persona_id": r["persona_id"],
            }
            for r in rows
        ]

    async def list_pending(self, created_by: str, persona_id: str) -> list[dict]:
        """All not-yet-delivered reminders CREATED BY this user and OWNED by this
        persona — the rows a `[REMIND_CANCEL:]` criterion is allowed to match.

        Same isolation contract as `get_pending_reminders`: user A can never see
        (or cancel) user B's rows, and Vultur can never touch what Insult agendó.
        Unlike the drain query this has no `remind_at <= now` cut — a reminder
        you want to cancel is by definition still in the future.
        """
        rows = await self._fetch(
            "SELECT id, channel_id, guild_id, created_by, description, remind_at, "
            "recurring, persona_id FROM reminders "
            "WHERE delivered = 0 AND created_by = $1 AND persona_id = $2 ORDER BY remind_at ASC",
            created_by,
            persona_id,
        )
        return [
            {
                "id": r["id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "description": r["description"],
                "remind_at": r["remind_at"],
                "recurring": r["recurring"],
                "persona_id": r["persona_id"],
            }
            for r in rows
        ]

    async def cancel_pending(self, created_by: str, persona_id: str, criterion: str) -> list[dict]:
        """Cancel this user's pending reminders whose description contains
        `criterion` (case-insensitive substring), scoped to this persona.

        Cancel = the repo's existing retire semantics: `delivered = 1` (the same
        flag `mark_reminder_delivered` and the stale-retire path use). The row is
        NEVER deleted — memory is append-only. A recurring reminder marked
        delivered stops recurring (the drain only rolls `delivered = 0` rows).

        Returns the cancelled rows (id + description) so the caller can log what
        actually died. Empty criterion cancels NOTHING — an empty substring
        matches everything, and a cancel-all was never asked for. Best-effort:
        a DB fault logs and returns [] (the turn already carried the ack).

        Surrounding quotes are stripped from the needle: the turn-context block
        renders each pending row as «description», so a persona quoting the
        fragment verbatim sends «la ropa» — which must still match the unquoted
        description instead of silently cancelling nothing after an affirmative
        ack.
        """
        needle = (criterion or "").strip().strip(_CRITERION_QUOTE_CHARS).strip().lower()
        if not needle:
            return []
        try:
            pending = await self.list_pending(created_by, persona_id)
            matched = [r for r in pending if needle in (r["description"] or "").lower()]
            if not matched:
                log.info(
                    "reminder_cancel_no_match",
                    created_by=created_by,
                    persona_id=persona_id,
                    criterion=criterion[:80],
                )
                return []
            ids = [int(r["id"]) for r in matched]
            tag = await self._execute(
                "UPDATE reminders SET delivered = 1 WHERE id = ANY($1::bigint[]) AND delivered = 0",
                ids,
            )
            log.info(
                "reminder_cancelled",
                reminder_ids=ids,
                cancelled=_affected_rows(tag),
                created_by=created_by,
                persona_id=persona_id,
                criterion=criterion[:80],
            )
            return matched
        except asyncpg.PostgresError as e:
            log.error(
                "reminder_cancel_failed",
                created_by=created_by,
                persona_id=persona_id,
                criterion=criterion[:80],
                error=str(e),
            )
            return []

    async def mark_reminder_delivered(self, reminder_id: int) -> None:
        try:
            await self._execute("UPDATE reminders SET delivered = 1 WHERE id = $1", reminder_id)
        except asyncpg.PostgresError as e:
            log.error("reminder_mark_delivered_failed", reminder_id=reminder_id, error=str(e))

    async def update_reminder_time(self, reminder_id: int, new_remind_at: float) -> None:
        """For recurring reminders: bump remind_at forward after a delivery."""
        try:
            await self._execute(
                "UPDATE reminders SET remind_at = $1 WHERE id = $2",
                new_remind_at,
                reminder_id,
            )
        except asyncpg.PostgresError as e:
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
        i = 1
        if new_remind_at is not None:
            sets.append(f"remind_at = ${i}")
            params.append(new_remind_at)
            i += 1
        if new_description is not None:
            sets.append(f"description = ${i}")
            params.append(new_description)
            i += 1
        if not sets:
            return False
        params.append(reminder_id)
        try:
            tag = await self._execute(
                f"UPDATE reminders SET {', '.join(sets)} WHERE id = ${i} AND delivered = 0",  # noqa: S608
                *params,
            )
            return _affected_rows(tag) > 0
        except asyncpg.PostgresError as e:
            log.error("reminder_update_fields_failed", reminder_id=reminder_id, error=str(e))
            return False

    async def get_channel_reminders(self, channel_id: str) -> list[dict]:
        """All pending (not-yet-delivered) reminders for a channel."""
        rows = await self._fetch(
            "SELECT id, channel_id, guild_id, created_by, description, remind_at, "
            "mention_user_ids, recurring FROM reminders "
            "WHERE channel_id = $1 AND delivered = 0 ORDER BY remind_at ASC",
            channel_id,
        )
        return [
            {
                "id": r["id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "description": r["description"],
                "remind_at": r["remind_at"],
                "mention_user_ids": r["mention_user_ids"],
                "recurring": r["recurring"],
            }
            for r in rows
        ]

    async def set_snooze_msg_id(self, reminder_id: int, msg_id: int) -> None:
        """Tag a reminder with the Discord message id where it was delivered.

        Used by the snooze flow: when a user reacts to that delivered message
        with ⏰/⏭️/📅 we look up the reminder by message id and recreate it
        with a future remind_at."""
        try:
            await self._execute(
                "UPDATE reminders SET snooze_msg_id = $1 WHERE id = $2",
                msg_id,
                reminder_id,
            )
        except asyncpg.PostgresError as e:
            log.error("reminder_set_snooze_msg_failed", reminder_id=reminder_id, error=str(e))

    async def get_reminder_for_snooze(self, msg_id: int) -> dict | None:
        """Look up the (delivered) reminder whose snooze_msg_id matches.

        Returns the columns needed to recreate the reminder (channel_id,
        guild_id, created_by, description, mention_user_ids). Returns None
        if no row matches — protects against snooze attempts on stale or
        already-snoozed messages."""
        row = await self._fetchrow(
            "SELECT id, channel_id, guild_id, created_by, description, mention_user_ids "
            "FROM reminders WHERE snooze_msg_id = $1 LIMIT 1",
            msg_id,
        )
        if not row:
            return None
        return {
            "id": row["id"],
            "channel_id": row["channel_id"],
            "guild_id": row["guild_id"],
            "created_by": row["created_by"],
            "description": row["description"],
            "mention_user_ids": row["mention_user_ids"],
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
        try:
            await self._execute(
                "UPDATE reminders SET ack_msg_id = $1, delivered_at = $2 WHERE id = $3",
                ack_msg_id,
                delivered_at,
                reminder_id,
            )
        except asyncpg.PostgresError as e:
            log.error("reminder_set_ack_metadata_failed", reminder_id=reminder_id, error=str(e))

    async def mark_ack_received(self, ack_msg_id: int) -> bool:
        """Mark a reminder as acknowledged when the user reacts ✅. Returns
        True if a row was updated — False means no reminder matches that
        message id (already acked, expired, or never existed)."""
        try:
            tag = await self._execute(
                "UPDATE reminders SET ack_received = 1 WHERE ack_msg_id = $1 AND ack_received = 0",
                ack_msg_id,
            )
            return _affected_rows(tag) > 0
        except asyncpg.PostgresError as e:
            log.error("reminder_mark_ack_failed", ack_msg_id=ack_msg_id, error=str(e))
            return False

    async def get_ack_overdue(self, now: float, timeout_seconds: float, max_retries: int) -> list[dict]:
        """Reminders whose ack window has lapsed without a ✅ and that have
        not yet been re-fired (ack_retry_count < max_retries). The returned
        dicts carry the columns needed to enqueue a new pending reminder."""
        rows = await self._fetch(
            "SELECT id, channel_id, guild_id, created_by, description, mention_user_ids, ack_retry_count "
            "FROM reminders "
            "WHERE requires_ack = 1 AND ack_received = 0 AND delivered = 1 "
            "AND ack_retry_count < $1 AND delivered_at IS NOT NULL AND delivered_at <= $2",
            max_retries,
            now - timeout_seconds,
        )
        return [
            {
                "id": r["id"],
                "channel_id": r["channel_id"],
                "guild_id": r["guild_id"],
                "created_by": r["created_by"],
                "description": r["description"],
                "mention_user_ids": r["mention_user_ids"],
                "ack_retry_count": r["ack_retry_count"],
            }
            for r in rows
        ]

    async def increment_ack_retry(self, reminder_id: int) -> None:
        """Bump the retry counter so we don't fire the same overdue ack twice."""
        try:
            await self._execute(
                "UPDATE reminders SET ack_retry_count = ack_retry_count + 1 WHERE id = $1",
                reminder_id,
            )
        except asyncpg.PostgresError as e:
            log.error("reminder_increment_ack_retry_failed", reminder_id=reminder_id, error=str(e))

    async def clear_snooze_msg_id(self, msg_id: int) -> None:
        """Detach the snooze pointer so a second reaction can't double-fire."""
        try:
            await self._execute(
                "UPDATE reminders SET snooze_msg_id = NULL WHERE snooze_msg_id = $1",
                msg_id,
            )
        except asyncpg.PostgresError as e:
            log.error("reminder_clear_snooze_msg_failed", msg_id=msg_id, error=str(e))

    async def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a NOT-yet-delivered reminder. Returns True if a row was removed."""
        try:
            tag = await self._execute(
                "DELETE FROM reminders WHERE id = $1 AND delivered = 0",
                reminder_id,
            )
            deleted = _affected_rows(tag) > 0
            if deleted:
                log.info("reminder_deleted", reminder_id=reminder_id)
            else:
                log.warning("reminder_delete_not_found", reminder_id=reminder_id)
            return deleted
        except asyncpg.PostgresError as e:
            log.error("reminder_delete_failed", reminder_id=reminder_id, error=str(e))
            return False
