"""Durable deep-research jobs — the deferred "te lo dejo aquí" made real."""

from __future__ import annotations

import structlog

from persona_core.markers import strip_delivery_markers
from persona_core.memory import MemoryStore
from persona_core.runner.agent_client import AgentRunnerClient
from persona_gateway.config import CONFIG
from persona_gateway.delivery import send_chunked
from persona_gateway.workers._host import GatewayHost, host_bot_id
from shared.personas import Persona

log = structlog.get_logger()

_FRAMING = (
    "TAREA DE INVESTIGACIÓN DIFERIDA que TÚ aceptaste hace un rato en este canal. "
    "Investígala a fondo AHORA (usa WebSearch/WebFetch si te sirve) y entrega el reporte "
    "COMPLETO, en tu propia voz, como quien vuelve de la madriguera con lo que fue a buscar. "
    "Este ES el 'después' que prometiste: NO vuelvas a diferir, NO prometas traerlo luego, "
    "entrega el contenido ya. Petición original del usuario:\n\n{prompt}"
)


class ResearchWorker:
    """Drain THIS persona's queued research jobs and post each report in its voice."""

    def __init__(self, persona: Persona, memory: MemoryStore, agent_client: AgentRunnerClient) -> None:
        self.persona = persona
        self.memory = memory
        self.agent_client = agent_client

    async def drain(self, host: GatewayHost) -> None:
        """Run each queued job on the runner (WebSearch, long reasoning) and post
        the report back. Crash-survivable: rows persist, a job stuck 'running'
        after a restart is recovered by the stale sweep; the loop never overlaps
        itself (discord.ext.tasks)."""
        try:
            await self.memory.reset_stale_research_jobs(CONFIG.research_timeout_s * 2)
            jobs = await self.memory.get_pending_research_jobs(
                limit=CONFIG.research_batch, persona_id=self.persona.persona_id
            )
        except Exception:
            log.exception("research_drain_fetch_failed", persona_id=self.persona.persona_id)
            return
        for job in jobs:
            await self.run_job(job, host)

    async def run_job(self, job: dict, host: GatewayHost) -> None:
        job_id = job["id"]
        await self.memory.mark_research_running(job_id)
        channel = host.get_channel(int(job["channel_id"]))
        if channel is None:
            log.warning("research_job_channel_gone", job_id=job_id, channel_id=job["channel_id"])
            await self.memory.mark_research_failed(job_id)
            return
        try:
            resp = await self.agent_client.chat(
                "",
                [{"role": "user", "content": _FRAMING.format(prompt=job["prompt"])}],
                # Isolated SDK session so the deep job never pollutes the channel's
                # live interactive thread; the result still posts to the real channel.
                channel_id=f"research-job-{job_id}",
                user_id=job["created_by"],
                persona_id=self.persona.persona_id,
                timeout_s=CONFIG.research_timeout_s,
            )
            # Deferred delivery: strip EVERY marker (a [REACT:] here has no live
            # message to act on and would leak as raw text — 2026-07-11 bug).
            result = strip_delivery_markers((resp.text or "").strip())
            if not result:
                raise RuntimeError("empty research result")
        except Exception:
            log.exception("research_job_run_failed", job_id=job_id, persona_id=self.persona.persona_id)
            if job.get("retry_count", 0) < CONFIG.research_max_retries:
                await self.memory.requeue_research_job(job_id)
            else:
                await self.memory.mark_research_failed(job_id)
            return
        try:
            await send_chunked(channel, result)
            await self.memory.store(
                job["channel_id"],
                host_bot_id(host),
                self.persona.display_name,
                "assistant",
                result,
                for_user_id=job["created_by"],
                guild_id=job.get("guild_id"),
                channel_name=None,
                model_used=getattr(resp, "model_used", None),
            )
            await self.memory.mark_research_done(job_id, result)
            log.info(
                "research_job_delivered",
                job_id=job_id,
                persona_id=self.persona.persona_id,
                chars=len(result),
            )
        except Exception:
            log.exception("research_job_deliver_failed", job_id=job_id, persona_id=self.persona.persona_id)
            await self.memory.mark_research_failed(job_id)
