"""Scheduling facade — reminders, research jobs, agendas."""

from __future__ import annotations

from khimeras_shared.memory.repositories import (
    AgendasRepository,
    RemindersRepository,
    ResearchJobsRepository,
)


class SchedulingFacade:
    _reminders: RemindersRepository
    _research_jobs: ResearchJobsRepository
    _agendas: AgendasRepository

    # -- Reminders --

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
        return await self._reminders.save_reminder(
            channel_id,
            guild_id,
            created_by,
            description,
            remind_at,
            mention_user_ids,
            recurring,
            requires_ack=requires_ack,
            persona_id=persona_id,
        )

    async def get_pending_reminders(self, now: float, persona_id: str | None = None) -> list[dict]:
        return await self._reminders.get_pending_reminders(now, persona_id=persona_id)

    async def set_ack_metadata(self, reminder_id: int, ack_msg_id: int, delivered_at: float) -> None:
        await self._reminders.set_ack_metadata(reminder_id, ack_msg_id, delivered_at)

    async def mark_ack_received(self, ack_msg_id: int) -> bool:
        return await self._reminders.mark_ack_received(ack_msg_id)

    async def get_ack_overdue(self, now: float, timeout_seconds: float, max_retries: int) -> list[dict]:
        return await self._reminders.get_ack_overdue(now, timeout_seconds, max_retries)

    async def increment_ack_retry(self, reminder_id: int) -> None:
        await self._reminders.increment_ack_retry(reminder_id)

    async def mark_reminder_delivered(self, reminder_id: int) -> None:
        await self._reminders.mark_reminder_delivered(reminder_id)

    async def update_reminder_time(self, reminder_id: int, new_remind_at: float) -> None:
        await self._reminders.update_reminder_time(reminder_id, new_remind_at)

    async def update_reminder_fields(
        self,
        reminder_id: int,
        *,
        new_remind_at: float | None = None,
        new_description: str | None = None,
    ) -> bool:
        return await self._reminders.update_reminder_fields(
            reminder_id,
            new_remind_at=new_remind_at,
            new_description=new_description,
        )

    async def get_channel_reminders(self, channel_id: str) -> list[dict]:
        return await self._reminders.get_channel_reminders(channel_id)

    async def list_pending_reminders(self, created_by: str, persona_id: str) -> list[dict]:
        return await self._reminders.list_pending(created_by, persona_id)

    async def cancel_pending_reminders(self, *, created_by: str, persona_id: str, criterion: str) -> list[dict]:
        return await self._reminders.cancel_pending(created_by, persona_id, criterion)

    async def delete_reminder(self, reminder_id: int) -> bool:
        return await self._reminders.delete_reminder(reminder_id)

    async def set_snooze_msg_id(self, reminder_id: int, msg_id: int) -> None:
        await self._reminders.set_snooze_msg_id(reminder_id, msg_id)

    async def get_reminder_for_snooze(self, msg_id: int) -> dict | None:
        return await self._reminders.get_reminder_for_snooze(msg_id)

    async def clear_snooze_msg_id(self, msg_id: int) -> None:
        await self._reminders.clear_snooze_msg_id(msg_id)

    # -- Research jobs --

    async def save_research_job(
        self,
        channel_id: str,
        guild_id: str | None,
        created_by: str,
        prompt: str,
        persona_id: str | None = None,
    ) -> int:
        return await self._research_jobs.save_job(channel_id, guild_id, created_by, prompt, persona_id)

    async def get_pending_research_jobs(self, limit: int = 3, persona_id: str | None = None) -> list[dict]:
        return await self._research_jobs.get_pending_jobs(limit, persona_id)

    async def mark_research_running(self, job_id: int) -> None:
        await self._research_jobs.mark_running(job_id)

    async def mark_research_done(self, job_id: int, result: str) -> None:
        await self._research_jobs.mark_done(job_id, result)

    async def mark_research_failed(self, job_id: int) -> None:
        await self._research_jobs.mark_failed(job_id)

    async def requeue_research_job(self, job_id: int) -> None:
        await self._research_jobs.requeue(job_id)

    async def reset_stale_research_jobs(self, older_than_s: float) -> int:
        return await self._research_jobs.reset_stale_running(older_than_s)

    # -- Agendas --

    async def save_agenda(
        self,
        persona_id: str | None,
        channel_id: str,
        guild_id: str | None,
        created_by: str,
        goal: str,
        cadence_hours: float = 24.0,
    ) -> int:
        return await self._agendas.save_agenda(persona_id, channel_id, guild_id, created_by, goal, cadence_hours)

    async def get_due_agendas(self, now: float, limit: int = 3, persona_id: str | None = None) -> list[dict]:
        return await self._agendas.get_due_agendas(now, limit, persona_id)

    async def mark_agenda_ran(self, agenda_id: int, now: float) -> None:
        await self._agendas.mark_agenda_ran(agenda_id, now)

    async def deactivate_agenda(self, agenda_id: int) -> None:
        await self._agendas.deactivate_agenda(agenda_id)

    async def get_channel_agendas(self, channel_id: str) -> list[dict]:
        return await self._agendas.get_channel_agendas(channel_id)
