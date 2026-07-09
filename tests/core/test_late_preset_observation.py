"""A preset classification that blows the ceiling must be OBSERVED, not cancelled.

Prod evidence (2026-07-09, 7d window): 210 of 219 turns logged
`preset_llm_timeout_fallback` — 95.9%. The Haiku classifier never once beat its
1500ms ceiling, so the "regex fallback" was in fact the only classifier running.
Nobody could see it, because the fallback event logged the CEILING and never the
latency that blew it, and `task.cancel()` destroyed the answer the runner had
already been paid to produce (`/v1/judge` spawns a Node subprocess per call).
"""

from __future__ import annotations

import asyncio
import time

import pytest
from structlog.testing import capture_logs

from personas.insult.composition import _LATE_PRESET_TASKS, _observe_late_preset
from personas.insult.core.contracts.presets import PresetMode, PresetSelection


def _sel(mode: PresetMode) -> PresetSelection:
    return PresetSelection(mode=mode)


async def _slow(result, delay=0.02):
    await asyncio.sleep(delay)
    return result


@pytest.mark.asyncio
async def test_late_result_is_logged_with_the_latency_the_ceiling_hid():
    regex = _sel(PresetMode.DEFAULT_ABRASIVE)
    task = asyncio.create_task(_slow(_sel(PresetMode.RESPECTFUL_SERIOUS)))
    started = time.monotonic()

    with capture_logs() as logs:
        _observe_late_preset(task, started, regex, timeout_s=0.001)
        await task
        await asyncio.sleep(0)

    ev = next(e for e in logs if e["event"] == "preset_llm_late_result")
    assert ev["timeout_ms"] == 1
    assert ev["latency_ms"] >= 20, "the real latency must be reported, not the ceiling"
    assert ev["llm_mode"] == PresetMode.RESPECTFUL_SERIOUS.value
    assert ev["regex_mode"] == PresetMode.DEFAULT_ABRASIVE.value
    assert ev["would_have_diverged"] is True


@pytest.mark.asyncio
async def test_the_timed_out_task_is_not_cancelled():
    """RESISTANCE: the whole point is that we already paid for this call."""
    task = asyncio.create_task(_slow(_sel(PresetMode.PLAYFUL_ROAST)))
    _observe_late_preset(task, time.monotonic(), _sel(PresetMode.PLAYFUL_ROAST), timeout_s=0.001)
    await task
    assert not task.cancelled()
    assert task.result().mode is PresetMode.PLAYFUL_ROAST


@pytest.mark.asyncio
async def test_agreement_is_logged_as_no_divergence():
    task = asyncio.create_task(_slow(_sel(PresetMode.PLAYFUL_ROAST)))
    with capture_logs() as logs:
        _observe_late_preset(task, time.monotonic(), _sel(PresetMode.PLAYFUL_ROAST), timeout_s=0.001)
        await task
        await asyncio.sleep(0)
    ev = next(e for e in logs if e["event"] == "preset_llm_late_result")
    assert ev["would_have_diverged"] is False


@pytest.mark.asyncio
async def test_late_failure_does_not_raise_into_the_turn():
    async def _boom():
        raise RuntimeError("runner died")

    task = asyncio.create_task(_boom())
    with capture_logs() as logs:
        _observe_late_preset(task, time.monotonic(), _sel(PresetMode.DEFAULT_ABRASIVE), timeout_s=0.001)
        with pytest.raises(RuntimeError):
            await task
        await asyncio.sleep(0)
    assert any(e["event"] == "preset_llm_late_failed" for e in logs)


@pytest.mark.asyncio
async def test_observer_does_not_leak_the_task_reference():
    """Without a strong ref the loop can GC a bare task mid-flight; without the
    discard it grows forever. Both are bugs, so pin both ends."""
    task = asyncio.create_task(_slow(_sel(PresetMode.DEFAULT_ABRASIVE)))
    _observe_late_preset(task, time.monotonic(), _sel(PresetMode.DEFAULT_ABRASIVE), timeout_s=0.001)
    assert task in _LATE_PRESET_TASKS
    await task
    await asyncio.sleep(0)
    assert task not in _LATE_PRESET_TASKS
