"""Durable deep-research drain loop for the HOST persona (Insult).

The sibling counterpart lives in ``persona_gateway.gateway`` (``_research_drain`` /
``_run_research_job``); this is the SAME durable-worker path but for Insult, which
runs in the ``personas/insult`` process (the ``discord-bot`` Container App), NOT in
the gateway. Insult posts the report back under its OWN Discord identity.

Contract mirrors the sibling path against the shared ``research_jobs`` table:

- A turn accepts a heavy research request and emits ``[RESEARCH: <prompt>]``; the
  plumbing (stages.py post-LLM, wired separately) queues a row with
  ``persona_id = NULL`` — Insult's jobs are the persona-less ones.
- This loop drains ONLY Insult's jobs (``persona_id is None``). Sibling jobs
  (``persona_id`` set) are drained by the gateway; we skip them.
- Each job runs on the runner with a generous read timeout (WebSearch + long
  reasoning), the report is chunked to Discord and posted, and the row is closed.

Crash-survivable: rows persist; a job stuck ``running`` past the stale window is
recovered by ``reset_stale_research_jobs``; the loop never overlaps itself
(``discord.ext.tasks``) and its whole body is guarded so a bad turn never kills it.
"""

from __future__ import annotations

import structlog
from discord.ext import tasks

from khimeras_shared.markers import strip_delivery_markers
from khimeras_shared.version import VERSION_TAG

log = structlog.get_logger()

RESEARCH_DRAIN_SECONDS = 45
RESEARCH_TIMEOUT_S = 360.0
RESEARCH_STALE_SECONDS = 720.0
RESEARCH_MAX_RETRIES = 2
DISCORD_LIMIT = 1990  # headroom under Discord's 2000-char message cap


def chunk(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Split a reply into Discord-sized pieces on paragraph/space boundaries."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return parts


async def _run_research_job(bot, container, memory, job: dict) -> None:
    """Run ONE Insult research job on the runner and post the report back."""
    job_id = job["id"]
    await memory.mark_research_running(job_id)
    channel = bot.get_channel(int(job["channel_id"]))
    if channel is None:
        log.warning("research_job_channel_gone", job_id=job_id, channel_id=job["channel_id"])
        await memory.mark_research_failed(job_id)
        return
    try:
        framing = (
            "TAREA DE INVESTIGACIÓN DIFERIDA que TÚ aceptaste hace un rato en este canal. "
            "Investígala a fondo AHORA (usa WebSearch/WebFetch si te sirve) y entrega el reporte "
            "COMPLETO, en tu propia voz, como quien vuelve de la madriguera con lo que fue a buscar. "
            "Este ES el 'después' que prometiste: NO vuelvas a diferir, NO prometas traerlo luego, "
            "entrega el contenido ya. Petición original del usuario:\n\n"
            f"{job['prompt']}"
        )
        resp = await container.agent_client.chat(
            "",
            [{"role": "user", "content": framing}],
            # Isolated SDK session so the deep job never pollutes the channel's
            # live interactive thread; the result still posts to the real channel.
            channel_id=f"research-job-{job_id}",
            user_id=job["created_by"],
            persona_id=None,
            timeout_s=RESEARCH_TIMEOUT_S,
        )
        result = strip_delivery_markers((resp.text or "").strip())
        if not result:
            raise RuntimeError("empty research result")
    except Exception:
        log.exception("research_job_run_failed", job_id=job_id)
        if job.get("retry_count", 0) < RESEARCH_MAX_RETRIES:
            await memory.requeue_research_job(job_id)
        else:
            await memory.mark_research_failed(job_id)
        return
    try:
        pieces = chunk(result)
        tag = f"\n-# {VERSION_TAG}"
        if pieces and len(pieces[-1]) + len(tag) <= 2000:
            pieces[-1] += tag
        for piece in pieces:
            await channel.send(piece)
        await memory.mark_research_done(job_id, result)
        log.info("research_job_delivered", job_id=job_id, chars=len(result))
    except Exception:
        log.exception("research_job_deliver_failed", job_id=job_id)
        await memory.mark_research_failed(job_id)


async def run_research_drain(bot, container, memory) -> None:
    """One drain pass: recover stale jobs, then run each of Insult's queued jobs.

    ``get_pending_research_jobs(limit, persona_id=None)`` returns ALL queued jobs
    (it does not filter when ``persona_id`` is None), so we FILTER client-side:
    only ``persona_id is None`` rows are Insult's. Sibling jobs are the gateway's;
    touching them here would double-drain them.
    """
    await memory.reset_stale_research_jobs(RESEARCH_STALE_SECONDS)
    jobs = await memory.get_pending_research_jobs(limit=2, persona_id=None)
    for job in jobs:
        if job.get("persona_id") is not None:
            continue  # sibling's job — the gateway drains it, not us
        await _run_research_job(bot, container, memory, job)


def build_research_tasks(bot, container, memory) -> tasks.Loop:
    """Return the (unstarted) Insult research-drain loop."""

    @tasks.loop(seconds=RESEARCH_DRAIN_SECONDS)
    async def _research_drain_task():
        try:
            await run_research_drain(bot, container, memory)
        except Exception:
            log.exception("research_drain_failed")

    return _research_drain_task
