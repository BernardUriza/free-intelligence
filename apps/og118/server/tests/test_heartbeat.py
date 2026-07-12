"""The turn must show a sign of life while it is QUIET.

The P0 this prevents: a client's idle watchdog cannot tell "the model is
thinking" from "the backend hung" — both are silence — and silence is NORMAL
here. An external element answers in ONE shot after up to 95s
(external_engine._TIMEOUT) and says nothing until then; a local turn can think
far longer than a token gap. og118 shipped with no heartbeat at all, so the
browser killed healthy turns at 60s, DISCARDED what the user had written, and
showed "la respuesta tardó demasiado" while the backend was still working.
"""

from __future__ import annotations

import asyncio
import time

import pytest

import app as app_module


async def _collect(agen) -> list[dict]:
    return [ev async for ev in agen]


@pytest.mark.asyncio
async def test_a_quiet_turn_still_reports_it_is_alive() -> None:
    async def quiet_then_answer():
        await asyncio.sleep(0.35)
        yield {"type": "text", "text": "por fin"}

    started = time.monotonic()
    events = await _collect(app_module._with_heartbeat(quiet_then_answer(), interval=0.1))
    elapsed = time.monotonic() - started

    pings = [e for e in events if e["type"] == "ping"]
    assert len(pings) >= 2, f"a {elapsed:.2f}s silence produced no sign of life: {events}"
    # The answer still arrives, last, unchanged.
    assert events[-1] == {"type": "text", "text": "por fin"}


@pytest.mark.asyncio
async def test_a_talkative_turn_gets_no_pings() -> None:
    """The heartbeat fills SILENCE — it never pads a stream that is already flowing."""

    async def chatty():
        for i in range(5):
            yield {"type": "text", "text": str(i)}

    events = await _collect(app_module._with_heartbeat(chatty(), interval=5.0))
    assert [e["type"] for e in events] == ["text"] * 5


@pytest.mark.asyncio
async def test_an_error_mid_turn_survives_the_wrapper() -> None:
    """A crash inside the turn must reach the client as an error event, not as a
    dead generator that leaves the UI spinning forever."""

    async def boom():
        yield {"type": "text", "text": "empiezo"}
        raise RuntimeError("el runner explotó")

    events = await _collect(app_module._with_heartbeat(boom(), interval=5.0))
    assert events[0] == {"type": "text", "text": "empiezo"}
    assert events[-1]["type"] == "error"
    assert "explotó" in events[-1]["message"]


@pytest.mark.asyncio
async def test_the_interval_is_well_under_the_client_watchdog() -> None:
    """15s vs the shell's 60s idle budget: a healthy turn re-arms it several times
    over before it can ever fire."""
    assert app_module.HEARTBEAT_INTERVAL_S < 60 / 3
