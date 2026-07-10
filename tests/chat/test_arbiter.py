"""Unit tests for the DeMux arbiter (supervise_runner_turn).

The arbiter replaces a blind read timeout: it grants the estimated budget, and
past it extends a runner still answering /health, only failing over when the
runner truly stops answering or the hard cap is hit. These pin each branch with
controllable in-flight tasks + a mocked health probe — no network, no real clock
beyond tens of milliseconds.
"""

from __future__ import annotations

import asyncio

import pytest

from khimeras_shared.runner.agent_client import PersonaTurnError, RunnerDownError
from personas.insult.cogs.chat._arbiter import supervise_runner_turn


async def _alive():
    return {"status": "ok"}


async def _dead():
    return {"status": "unreachable", "error": "connect refused"}


@pytest.mark.asyncio
async def test_completes_within_budget_never_probes_or_notifies():
    async def quick():
        return "done-fast"

    probes = []

    async def probe():
        probes.append(1)
        return {"status": "ok"}

    notices = []

    async def notice():
        notices.append(1)

    task = asyncio.create_task(quick())
    result = await supervise_runner_turn(
        task,
        budget_s=1.0,
        hard_cap_s=2.0,
        checkpoint_s=0.1,
        health_probe=probe,
        on_budget_exceeded=notice,
    )
    assert result == "done-fast"
    assert probes == []  # never had to check liveness
    assert notices == []  # never told the user "sigo en ello"


@pytest.mark.asyncio
async def test_slow_but_alive_runner_is_extended_not_failed_over():
    # THE incident case: the runner is slow (past the budget) but its /health
    # still answers → extend and let it finish. No RunnerDownError.
    async def slow():
        await asyncio.sleep(0.18)
        return "research-result"

    notices = []

    async def notice():
        notices.append(1)

    task = asyncio.create_task(slow())
    result = await supervise_runner_turn(
        task,
        budget_s=0.05,
        hard_cap_s=2.0,
        checkpoint_s=0.03,
        health_probe=_alive,
        on_budget_exceeded=notice,
    )
    assert result == "research-result"
    assert len(notices) == 1  # the "sigo en ello" fires exactly once


@pytest.mark.asyncio
async def test_dead_runner_raises_after_strikes_and_cancels_task():
    async def hang():
        await asyncio.sleep(100)
        return "never"

    task = asyncio.create_task(hang())
    with pytest.raises(RunnerDownError):
        await supervise_runner_turn(
            task,
            budget_s=0.02,
            hard_cap_s=5.0,
            checkpoint_s=0.02,
            health_probe=_dead,
            max_health_strikes=2,
        )
    await asyncio.sleep(0)  # let the cancellation settle
    assert task.done()


@pytest.mark.asyncio
async def test_one_unreachable_probe_does_not_kill_a_recovering_runner():
    # Resistance: a single blip must NOT fail the turn (max_health_strikes=2).
    # First probe unreachable, then alive → the runner recovers and finishes.
    calls = {"n": 0}

    async def flaky_probe():
        calls["n"] += 1
        return {"status": "unreachable"} if calls["n"] == 1 else {"status": "ok"}

    async def slow():
        await asyncio.sleep(0.2)
        return "recovered"

    task = asyncio.create_task(slow())
    result = await supervise_runner_turn(
        task,
        budget_s=0.03,
        hard_cap_s=3.0,
        checkpoint_s=0.03,
        health_probe=flaky_probe,
        max_health_strikes=2,
    )
    assert result == "recovered"


@pytest.mark.asyncio
async def test_hard_cap_cuts_even_an_alive_runner():
    async def hang():
        await asyncio.sleep(100)
        return "never"

    task = asyncio.create_task(hang())
    with pytest.raises(RunnerDownError):
        await supervise_runner_turn(
            task,
            budget_s=0.02,
            hard_cap_s=0.12,
            checkpoint_s=0.03,
            health_probe=_alive,  # alive the whole time, yet the cap still cuts
        )
    await asyncio.sleep(0)
    assert task.done()


@pytest.mark.asyncio
async def test_persona_turn_error_propagates_unchanged():
    # Resistance: a 4xx (the runner rejected the turn) must NOT be extended or
    # swallowed — it surfaces so the caller degrades honestly, never a fake-ALICE.
    async def bad():
        raise PersonaTurnError("runner 400")

    task = asyncio.create_task(bad())
    with pytest.raises(PersonaTurnError):
        await supervise_runner_turn(
            task,
            budget_s=1.0,
            hard_cap_s=2.0,
            checkpoint_s=0.1,
            health_probe=_alive,
        )


@pytest.mark.asyncio
async def test_probe_that_raises_counts_as_unreachable():
    async def hang():
        await asyncio.sleep(100)
        return "never"

    async def raising_probe():
        raise RuntimeError("probe boom")

    task = asyncio.create_task(hang())
    with pytest.raises(RunnerDownError):
        await supervise_runner_turn(
            task,
            budget_s=0.02,
            hard_cap_s=5.0,
            checkpoint_s=0.02,
            health_probe=raising_probe,
            max_health_strikes=1,
        )
