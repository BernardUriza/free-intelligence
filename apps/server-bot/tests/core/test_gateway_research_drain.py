"""Gateway research drain — the deferred "te lo dejo aquí" job actually RUNS.

Drives `PersonaClient._research_drain` directly, mirroring the reminder-drain
canonical suite. The fake repo models delivered/failed state (closed rows stop
being returned), so breaking `mark_research_done` in the worker turns the
no-re-delivery test red instead of passing on a hand-cleared list.

Positive (a pending job runs on the runner and its report lands in the channel)
+ resistance: a done job never re-runs, an empty queue is a silent no-op, a
runner/delivery failure never marks done nor kills the batch, and a sibling's
job is never this persona's to run.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from persona_gateway.config import CONFIG
from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


def _persona(persona_id: str = "vultur") -> Persona:
    return Persona(
        persona_id=persona_id,
        display_name=persona_id.capitalize(),
        persona_file=f"{persona_id}.md",
        token_env=f"{persona_id.upper()}_DISCORD_TOKEN",
    )


def _job(**over) -> dict:
    base = {
        "id": 7,
        "channel_id": "1489180895264116736",
        "guild_id": "G1",
        "created_by": "907264175246569543",
        "prompt": "compárame los mejores e-readers de tinta color",
        "retry_count": 0,
        "persona_id": "vultur",
    }
    base.update(over)
    return base


def _client(
    pending: list[dict],
    *,
    persona_id: str = "vultur",
    reply: str = "Reporte: el HiBreak Pro gana por pantalla y bootloader.",
):
    memory = MagicMock()
    closed: set[int] = set()

    async def _mark_done(job_id, result):
        closed.add(job_id)

    async def _mark_failed(job_id):
        closed.add(job_id)

    async def _requeue(job_id):
        for job in pending:
            if job["id"] == job_id:
                job["retry_count"] = job.get("retry_count", 0) + 1

    async def _get_pending(limit, persona_id=None):
        rows = [j for j in pending if j["id"] not in closed and j["persona_id"] == persona_id]
        return rows[:limit]

    memory.store = AsyncMock()
    memory.reset_stale_research_jobs = AsyncMock()
    memory.mark_research_running = AsyncMock()
    memory.mark_research_done = AsyncMock(side_effect=_mark_done)
    memory.mark_research_failed = AsyncMock(side_effect=_mark_failed)
    memory.requeue_research_job = AsyncMock(side_effect=_requeue)
    memory.get_pending_research_jobs = AsyncMock(side_effect=_get_pending)

    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply, model_used="claude"))

    client = PersonaClient(_persona(persona_id), memory, agent_client, intents=discord.Intents.none())
    channel = MagicMock()
    channel.send = AsyncMock()
    client.get_channel = MagicMock(return_value=channel)
    return client, memory, channel


def _sent(channel) -> str:
    return " ".join(str(c) for c in channel.send.call_args_list)


async def test_pending_job_runs_and_report_is_delivered():
    client, memory, channel = _client([_job()])

    await client._research_drain()

    assert channel.send.await_count >= 1
    assert "HiBreak" in _sent(channel)
    memory.mark_research_running.assert_awaited_once_with(7)
    job_id, result = memory.mark_research_done.await_args.args
    assert job_id == 7
    assert "HiBreak" in result
    memory.store.assert_awaited_once()
    memory.reset_stale_research_jobs.assert_awaited_once_with(CONFIG.research_timeout_s * 2)


async def test_job_runs_in_isolated_session_and_markers_are_stripped():
    """The deep job must not pollute the live channel thread, and a [REACT:]
    in a deferred delivery has no message to act on — it must never leak."""
    client, memory, channel = _client([_job()], reply="Te traigo el reporte. [REACT:🔥] Fin.")

    await client._research_drain()

    kwargs = client.agent_client.chat.await_args.kwargs
    assert kwargs["channel_id"] == "research-job-7"
    assert kwargs["persona_id"] == "vultur"
    assert kwargs["timeout_s"] == CONFIG.research_timeout_s
    assert "[REACT:" not in _sent(channel)
    assert "Te traigo el reporte." in _sent(channel)


async def test_done_job_is_not_rerun_next_tick():
    """RESISTENCIA: the delivered job must never run twice."""
    client, memory, channel = _client([_job()])

    await client._research_drain()
    first = channel.send.await_count

    await client._research_drain()

    assert client.agent_client.chat.await_count == 1
    assert channel.send.await_count == first
    assert memory.mark_research_done.await_count == 1


async def test_empty_queue_is_a_silent_noop():
    client, memory, channel = _client([])

    await client._research_drain()

    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()
    memory.mark_research_running.assert_not_awaited()
    memory.mark_research_done.assert_not_awaited()


async def test_runner_failure_requeues_and_never_marks_done():
    """RESISTENCIA: a dead runner leaves the job pending for retry, not done."""
    client, memory, channel = _client([_job()])
    client.agent_client.chat = AsyncMock(side_effect=RuntimeError("runner down"))

    await client._research_drain()

    channel.send.assert_not_awaited()
    memory.mark_research_done.assert_not_awaited()
    memory.mark_research_failed.assert_not_awaited()
    memory.requeue_research_job.assert_awaited_once_with(7)

    await client._research_drain()

    assert client.agent_client.chat.await_count == 2


async def test_empty_result_is_a_failure_not_a_delivery():
    client, memory, channel = _client([_job()], reply="")

    await client._research_drain()

    channel.send.assert_not_awaited()
    memory.mark_research_done.assert_not_awaited()
    memory.requeue_research_job.assert_awaited_once_with(7)


async def test_retries_exhausted_marks_failed():
    client, memory, channel = _client([_job(retry_count=CONFIG.research_max_retries)])
    client.agent_client.chat = AsyncMock(side_effect=RuntimeError("runner down"))

    await client._research_drain()

    memory.mark_research_failed.assert_awaited_once_with(7)
    memory.requeue_research_job.assert_not_awaited()


async def test_failing_delivery_marks_failed_not_done_and_batch_survives():
    """RESISTENCIA: a dead channel kills ONE job, not the loop; the posted-nothing
    job is never marked done."""
    client, memory, channel = _client([_job(id=1), _job(id=2)])
    broken = MagicMock()
    broken.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=403), "forbidden"))
    ok_channel = MagicMock()
    ok_channel.send = AsyncMock()
    client.get_channel = MagicMock(side_effect=[broken, ok_channel])

    await client._research_drain()

    ok_channel.send.assert_awaited()
    memory.mark_research_failed.assert_awaited_once_with(1)
    job_id, _ = memory.mark_research_done.await_args.args
    assert job_id == 2


async def test_sibling_job_is_never_run_by_this_persona():
    """RESISTENCIA: Vultur does NOT run the research Insult aceptó."""
    client, memory, channel = _client([_job(id=9, persona_id="insult")], persona_id="vultur")

    await client._research_drain()

    assert memory.get_pending_research_jobs.await_args.kwargs["persona_id"] == "vultur"
    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()
    memory.mark_research_done.assert_not_awaited()


async def test_channel_gone_marks_failed_without_running():
    client, memory, channel = _client([_job()])
    client.get_channel = MagicMock(return_value=None)

    await client._research_drain()

    client.agent_client.chat.assert_not_awaited()
    memory.mark_research_failed.assert_awaited_once_with(7)
    memory.mark_research_done.assert_not_awaited()


async def test_fetch_failure_is_survived_silently():
    client, memory, channel = _client([_job()])
    memory.get_pending_research_jobs = AsyncMock(side_effect=RuntimeError("pg down"))

    await client._research_drain()

    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()


async def test_batch_cap_limits_jobs_per_tick():
    jobs = [_job(id=i) for i in range(1, CONFIG.research_batch + 3)]
    client, memory, channel = _client(jobs)

    await client._research_drain()

    assert memory.get_pending_research_jobs.await_args.kwargs["limit"] == CONFIG.research_batch
    assert client.agent_client.chat.await_count == CONFIG.research_batch
