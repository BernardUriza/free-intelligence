"""Judge concurrency gate — serialize /v1/judge SDK calls (v3.9.96).

Phase 1 of the 2026-05-22 perf work. The judge endpoint spawns a fresh Node
subprocess per call and the SDK has no max_tokens cap; a consolidator backlog
fired ~25 concurrent judges on a 1-CPU/2Gi runner, OOM-killing the chat turns'
SDK and starving their CPU. The gate forces background judge work to queue
instead of piling up, protecting the interactive turns.
"""

from __future__ import annotations

import asyncio

import pytest

from insult.agent import runner


@pytest.fixture(autouse=True)
def _reset_semaphore():
    """Each test starts with a fresh semaphore bound to the test's loop."""
    runner._judge_semaphore = None
    yield
    runner._judge_semaphore = None


def test_semaphore_is_singleton_with_configured_bound():
    async def _check():
        s1 = runner._get_judge_semaphore()
        s2 = runner._get_judge_semaphore()
        assert s1 is s2
        # asyncio.Semaphore exposes its current value as _value when untouched
        assert s1._value == runner.JUDGE_MAX_CONCURRENCY

    asyncio.run(_check())


async def test_gate_serializes_concurrent_judges():
    """The core guarantee: no more than JUDGE_MAX_CONCURRENCY judge bodies run
    at once even when many are launched together (the consolidator burst)."""
    concurrent = 0
    max_seen = 0

    async def worker():
        nonlocal concurrent, max_seen
        async with runner._get_judge_semaphore():
            concurrent += 1
            max_seen = max(max_seen, concurrent)
            await asyncio.sleep(0.01)  # stand-in for the SDK call
            concurrent -= 1

    await asyncio.gather(*[worker() for _ in range(8)])
    assert max_seen <= runner.JUDGE_MAX_CONCURRENCY


async def test_locked_reports_true_under_contention():
    """`locked()` is what the handler uses to log `agent_runner_judge_queued`;
    confirm it reflects contention so the telemetry is truthful."""
    sem = runner._get_judge_semaphore()
    assert not sem.locked()
    async with sem:
        # with bound 1 the gate is now held → a second arrival would queue
        if runner.JUDGE_MAX_CONCURRENCY == 1:
            assert sem.locked()
