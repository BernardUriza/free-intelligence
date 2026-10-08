"""Reminders — the promise ("te lo recuerdo a las 8") finally kept."""

from __future__ import annotations

import time

import structlog

from persona_core.markers import strip_delivery_markers
from persona_core.memory import MemoryStore
from persona_core.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt
from persona_core.remind_marker import compute_next_occurrence
from persona_core.runner.agent_client import AgentRunnerClient
from persona_gateway.config import CONFIG
from persona_gateway.delivery import send_chunked
from persona_gateway.workers._host import GatewayHost, host_bot_id
from shared.personas import Persona

log = structlog.get_logger()


class ReminderWorker:
    """Fire THIS persona's due reminders; roll recurring ones forward, retire the rest."""

    def __init__(
        self,
        persona: Persona,
        memory: MemoryStore,
        agent_client: AgentRunnerClient,
        prompt_cache: PromptCache,
    ) -> None:
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client
        self._prompt_cache = prompt_cache

    async def drain(self, host: GatewayHost) -> None:
        """Rows are owned by the persona that scheduled them, so a sibling never
        delivers someone else's reminder and none is sent twice by two live bots.
        One bad row (channel gone, no perms) is logged and skipped; the rest land."""
        try:
            due = await self.memory.get_pending_reminders(time.time(), persona_id=self.persona.persona_id)
        except Exception:
            log.exception("reminder_drain_fetch_failed", persona_id=self.persona.persona_id)
            return
        for reminder in due:
            try:
                await self.deliver(reminder, host)
            except Exception:
                log.exception(
                    "reminder_deliver_failed",
                    reminder_id=reminder.get("id"),
                    persona_id=self.persona.persona_id,
                )

    async def deliver(self, reminder: dict, host: GatewayHost) -> None:
        reminder_id = reminder["id"]
        channel = host.get_channel(int(reminder["channel_id"]))
        if channel is None:
            await self.close(reminder)
            log.warning(
                "reminder_channel_gone",
                reminder_id=reminder_id,
                channel_id=reminder["channel_id"],
                persona_id=self.persona.persona_id,
            )
            return
        lateness = time.time() - float(reminder["remind_at"])
        if lateness > CONFIG.reminder_max_lateness_s:
            await self.close(reminder)
            log.warning(
                "reminder_retired_stale",
                reminder_id=reminder_id,
                persona_id=self.persona.persona_id,
                lateness_s=int(lateness),
            )
            return

        body = await self.reminder_text(reminder)
        mentions = " ".join(
            f"<@{uid.strip()}>" for uid in (reminder.get("mention_user_ids") or "").split(",") if uid.strip()
        )
        text = f"{mentions} {body}".strip() if mentions else body
        try:
            await send_chunked(channel, text)
        except Exception:
            # Transient (rate limit, blip) → the row stays pending and the next
            # tick retries. Permanent (channel deleted, permissions revoked) →
            # the staleness guard above retires it. Either way the loop lives and
            # the rest of the batch is delivered.
            log.exception(
                "reminder_send_failed",
                reminder_id=reminder_id,
                channel_id=reminder["channel_id"],
                persona_id=self.persona.persona_id,
            )
            return

        await self.close(reminder)
        try:
            await self.memory.store(
                reminder["channel_id"],
                host_bot_id(host),
                self.persona.display_name,
                "assistant",
                text,
                for_user_id=reminder["created_by"],
                guild_id=reminder.get("guild_id"),
                channel_name=None,
            )
        except Exception:
            log.exception("reminder_store_failed", reminder_id=reminder_id)
        log.info(
            "reminder_delivered",
            reminder_id=reminder_id,
            persona_id=self.persona.persona_id,
            channel_id=reminder["channel_id"],
            recurring=reminder.get("recurring"),
            lateness_s=int(lateness),
        )

    async def close(self, reminder: dict) -> None:
        """Retire the row so it never fires twice: a recurring reminder is rolled
        forward to its next future occurrence, a one-shot is marked delivered."""
        reminder_id = reminder["id"]
        recurring = reminder.get("recurring") or "none"
        next_at = compute_next_occurrence(float(reminder["remind_at"]), recurring)
        if next_at is None:
            await self.memory.mark_reminder_delivered(reminder_id)
            return
        await self.memory.update_reminder_time(reminder_id, next_at)
        log.info(
            "reminder_rescheduled",
            reminder_id=reminder_id,
            persona_id=self.persona.persona_id,
            recurring=recurring,
            next_at=next_at,
        )

    async def reminder_text(self, reminder: dict) -> str:
        """The reminder in the persona's own voice, via the runner. A plain
        fallback is ALWAYS returned when the runner is down or answers empty —
        the user gets the content of their reminder no matter what."""
        description = reminder["description"]
        fallback = f"⏰ Recordatorio: {description}"
        try:
            prompt = load_prompt(SHARED_PROMPTS_DIR, "reminder_delivery", self._prompt_cache).format(
                description=description
            )
            resp = await self.agent_client.chat(
                "",
                [{"role": "user", "content": prompt}],
                channel_id=f"reminder-{reminder['id']}",
                user_id=reminder["created_by"],
                persona_id=self.persona.persona_id,
                timeout_s=CONFIG.reminder_timeout_s,
            )
            text = strip_delivery_markers((resp.text or "").strip())
        except Exception:
            log.exception(
                "reminder_voice_failed",
                reminder_id=reminder["id"],
                persona_id=self.persona.persona_id,
            )
            return fallback
        if not text:
            log.info("reminder_voice_empty", reminder_id=reminder["id"], persona_id=self.persona.persona_id)
            return fallback
        return text
