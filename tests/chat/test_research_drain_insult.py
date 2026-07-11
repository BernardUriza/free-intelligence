"""Insult's durable research-drain loop — run, skip-sibling, requeue-on-empty.

Mirrors the gateway's ``_research_drain`` path but for the HOST (Insult): it
drains ONLY persona-less jobs (``persona_id is None``), posts the runner's report
back to the channel under Insult's identity, and closes the row. Sibling jobs
(``persona_id`` set) belong to the gateway and must be left untouched.

The loop is a ``discord.ext.tasks.Loop``; the testable body is the module-level
``run_research_drain`` coroutine the loop delegates to — driven here with mocks
(no network, no clock).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.tasks import research_jobs
from personas.insult.tasks.research_jobs import build_research_tasks, run_research_drain


def _memory(jobs: list[dict]) -> MagicMock:
    memory = MagicMock()
    memory.reset_stale_research_jobs = AsyncMock(return_value=0)
    memory.get_pending_research_jobs = AsyncMock(return_value=jobs)
    memory.mark_research_running = AsyncMock()
    memory.mark_research_done = AsyncMock()
    memory.mark_research_failed = AsyncMock()
    memory.requeue_research_job = AsyncMock()
    return memory


def _bot_with_channel() -> tuple[MagicMock, AsyncMock]:
    channel = MagicMock()
    channel.send = AsyncMock()
    bot = MagicMock()
    bot.get_channel = MagicMock(return_value=channel)
    return bot, channel


def _container(text: str) -> MagicMock:
    container = MagicMock()
    container.agent_client = MagicMock()
    container.agent_client.chat = AsyncMock(return_value=MagicMock(text=text))
    return container


def _insult_job(**over) -> dict:
    base = {
        "id": 1,
        "channel_id": "1489180895264116736",
        "guild_id": "9",
        "created_by": "907264175246569543",
        "persona_id": None,
        "prompt": "investiga la historia del anarquismo insurreccional",
        "retry_count": 0,
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_insult_job_runs_posts_and_marks_done():
    job = _insult_job()
    memory = _memory([job])
    bot, channel = _bot_with_channel()
    container = _container("Aquí va el reporte completo tras volver de la madriguera.")

    await run_research_drain(bot, container, memory)

    container.agent_client.chat.assert_awaited_once()
    # persona_id must be None (Insult), isolated research-job session id.
    _, kwargs = container.agent_client.chat.await_args
    assert kwargs["persona_id"] is None
    assert kwargs["channel_id"] == "research-job-1"
    assert kwargs["timeout_s"] == research_jobs.RESEARCH_TIMEOUT_S

    memory.mark_research_running.assert_awaited_once_with(1)
    channel.send.assert_awaited()  # report delivered
    memory.mark_research_done.assert_awaited_once()
    assert memory.mark_research_done.await_args.args[0] == 1
    memory.mark_research_failed.assert_not_awaited()
    memory.requeue_research_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_sibling_job_is_ignored():
    insult = _insult_job(id=1)
    alice = _insult_job(id=2, persona_id="alice")
    memory = _memory([insult, alice])
    bot, _ = _bot_with_channel()
    container = _container("reporte")

    await run_research_drain(bot, container, memory)

    # Only Insult's job (persona_id=None) is processed; the sibling's is the
    # gateway's to drain.
    container.agent_client.chat.assert_awaited_once()
    memory.mark_research_running.assert_awaited_once_with(1)
    # alice's id (2) is never claimed/failed/requeued here.
    for mock in (memory.mark_research_running, memory.mark_research_done, memory.mark_research_failed):
        for call in mock.await_args_list:
            assert call.args[0] != 2


@pytest.mark.asyncio
async def test_empty_result_requeues_when_retries_remain():
    job = _insult_job(retry_count=0)
    memory = _memory([job])
    bot, channel = _bot_with_channel()
    container = _container("")  # runner returned nothing → empty result

    await run_research_drain(bot, container, memory)

    memory.requeue_research_job.assert_awaited_once_with(1)
    memory.mark_research_failed.assert_not_awaited()
    memory.mark_research_done.assert_not_awaited()
    channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_result_fails_when_retries_exhausted():
    job = _insult_job(retry_count=research_jobs.RESEARCH_MAX_RETRIES)
    memory = _memory([job])
    bot, _ = _bot_with_channel()
    container = _container("")

    await run_research_drain(bot, container, memory)

    memory.mark_research_failed.assert_awaited_once_with(1)
    memory.requeue_research_job.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_channel_marks_failed():
    job = _insult_job()
    memory = _memory([job])
    bot = MagicMock()
    bot.get_channel = MagicMock(return_value=None)
    container = _container("reporte")

    await run_research_drain(bot, container, memory)

    memory.mark_research_failed.assert_awaited_once_with(1)
    container.agent_client.chat.assert_not_awaited()


def test_build_research_tasks_returns_unstarted_loop():
    bot, _ = _bot_with_channel()
    loop = build_research_tasks(bot, _container("x"), _memory([]))
    assert hasattr(loop, "start")
    assert not loop.is_running()
