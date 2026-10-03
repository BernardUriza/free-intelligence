"""Standing agendas — the autonomy trigger: pursue a goal and post UNPROMPTED."""

from __future__ import annotations

import time

import structlog

from persona_core.markers import strip_delivery_markers
from persona_core.memory import MemoryStore
from persona_core.proactive_agenda import frame_agenda_prompt, is_daytime, is_nothing_new
from persona_core.runner.agent_client import AgentRunnerClient
from persona_gateway.config import CONFIG
from persona_gateway.delivery import send_chunked
from persona_gateway.workers._host import GatewayHost, host_bot_id
from shared.personas import Persona
from shared.time_context import now_in_mexico_city

log = structlog.get_logger()


class AgendaWorker:
    """Pursue THIS persona's due standing agendas and post findings unprompted."""

    def __init__(self, persona: Persona, memory: MemoryStore, agent_client: AgentRunnerClient) -> None:
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client

    async def drain(self, host: GatewayHost) -> None:
        """Each due agenda is pursued; the per-agenda `cadence_hours` throttles
        real frequency. When the runner finds nothing new the persona stays QUIET.

        Outside waking hours nothing runs and nothing is marked ran, so a due
        agenda simply waits for the window to open instead of posting at 03:00.
        """
        if not is_daytime(now_in_mexico_city(), CONFIG.agenda_daytime_start, CONFIG.agenda_daytime_end):
            log.debug("agenda_outside_daytime_window", persona_id=self.persona.persona_id)
            return
        try:
            agendas = await self.memory.get_due_agendas(
                time.time(), limit=CONFIG.agenda_batch, persona_id=self.persona.persona_id
            )
        except Exception:
            log.exception("agenda_check_fetch_failed", persona_id=self.persona.persona_id)
            return
        for agenda in agendas:
            await self.run(agenda, host)

    async def run(self, agenda: dict, host: GatewayHost) -> None:
        agenda_id = agenda["id"]
        channel = host.get_channel(int(agenda["channel_id"]))
        if channel is None:
            log.warning("agenda_channel_gone", agenda_id=agenda_id, channel_id=agenda["channel_id"])
            await self.memory.mark_agenda_ran(agenda_id, time.time())
            return
        try:
            resp = await self.agent_client.chat(
                "",
                [{"role": "user", "content": frame_agenda_prompt(agenda["goal"])}],
                channel_id=f"agenda-{agenda_id}",
                user_id=agenda["created_by"],
                persona_id=self.persona.persona_id,
                timeout_s=CONFIG.agenda_timeout_s,
            )
            finding = strip_delivery_markers((resp.text or "").strip())
        except Exception:
            log.exception("agenda_run_failed", agenda_id=agenda_id, persona_id=self.persona.persona_id)
            # Do NOT mark ran on a transport failure — let it retry next cadence.
            return
        # Always mark ran (cadence advances); only POST when there's something new.
        await self.memory.mark_agenda_ran(agenda_id, time.time())
        if is_nothing_new(finding):
            log.info("agenda_nothing_new", agenda_id=agenda_id, persona_id=self.persona.persona_id)
            return
        try:
            await send_chunked(channel, finding)
            await self.memory.store(
                agenda["channel_id"],
                host_bot_id(host),
                self.persona.display_name,
                "assistant",
                finding,
                for_user_id=agenda["created_by"],
                guild_id=agenda.get("guild_id"),
                channel_name=None,
                model_used=getattr(resp, "model_used", None),
            )
            log.info(
                "agenda_finding_posted",
                agenda_id=agenda_id,
                persona_id=self.persona.persona_id,
                chars=len(finding),
            )
        except Exception:
            log.exception("agenda_deliver_failed", agenda_id=agenda_id, persona_id=self.persona.persona_id)
