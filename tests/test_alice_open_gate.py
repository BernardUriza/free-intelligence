"""Tests for ALICE's self-governing open-gate failover (alice 0.1.21).

`_should_open_gate` decides per turn whether ALICE covers a channel while Insult
is down. The safety-critical behavior:
  - "auto" mode opens ONLY while Insult is silent past the threshold, and stands
    back the moment he answers again (so the two bots don't double-reply once
    Insult recovers).
  - a health-query failure fails OPEN (cover, don't go silent).

Driven directly with a mock AliceMemory — no Postgres, no Discord.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from alice.cogs.chat import AliceChatCog
from alice.config import settings as alice_settings


def _make_cog(*, silent_s=None, raises=False):
    memory = MagicMock()
    if raises:
        memory.seconds_since_insult_reply = AsyncMock(side_effect=RuntimeError("pg down"))
    else:
        memory.seconds_since_insult_reply = AsyncMock(return_value=silent_s)
    return AliceChatCog(bot=MagicMock(), memory=memory, llm=MagicMock(), persona=MagicMock())


@pytest.fixture(autouse=True)
def _reset_gate_settings():
    """Snapshot + restore the global open-gate settings each test."""
    snap = (
        alice_settings.open_gate_mode,
        alice_settings.open_gate_enabled,
        alice_settings.open_gate_silence_threshold_s,
    )
    yield
    (
        alice_settings.open_gate_mode,
        alice_settings.open_gate_enabled,
        alice_settings.open_gate_silence_threshold_s,
    ) = snap


# --- mode: on / off -------------------------------------------------------


async def test_mode_on_always_opens():
    alice_settings.open_gate_mode = "on"
    cog = _make_cog(silent_s=1.0)  # Insult just spoke — irrelevant in 'on'
    assert await cog._should_open_gate("C1") == "open_gate_on"


async def test_mode_off_never_opens():
    alice_settings.open_gate_mode = "off"
    alice_settings.open_gate_enabled = False
    cog = _make_cog(silent_s=None)  # Insult never spoke — still closed in 'off'
    assert await cog._should_open_gate("C1") is None


async def test_deprecated_enabled_flag_treated_as_on():
    """Backward compat: open_gate_enabled=True with mode left 'off' → 'on'."""
    alice_settings.open_gate_mode = "off"
    alice_settings.open_gate_enabled = True
    cog = _make_cog(silent_s=1.0)
    assert await cog._should_open_gate("C1") == "open_gate_on"


# --- mode: auto -----------------------------------------------------------


async def test_auto_stands_back_when_insult_recent():
    """Resistance case: Insult answered 30s ago (< 300s threshold) → ALICE must
    NOT open the gate (avoids double-reply once Insult is healthy)."""
    alice_settings.open_gate_mode = "auto"
    alice_settings.open_gate_silence_threshold_s = 300.0
    cog = _make_cog(silent_s=30.0)
    assert await cog._should_open_gate("C1") is None


async def test_auto_opens_when_insult_silent_past_threshold():
    """Positive case: Insult silent 600s (> 300s) → ALICE covers."""
    alice_settings.open_gate_mode = "auto"
    alice_settings.open_gate_silence_threshold_s = 300.0
    cog = _make_cog(silent_s=600.0)
    reason = await cog._should_open_gate("C1")
    assert reason is not None
    assert reason.startswith("open_gate_auto_insult_silent_")


async def test_auto_opens_when_insult_never_spoke():
    alice_settings.open_gate_mode = "auto"
    cog = _make_cog(silent_s=None)
    assert await cog._should_open_gate("C1") == "open_gate_auto_insult_never_spoke"


async def test_auto_fails_open_on_healthcheck_error():
    """A Postgres hiccup must not silence ALICE — fail OPEN."""
    alice_settings.open_gate_mode = "auto"
    cog = _make_cog(raises=True)
    assert await cog._should_open_gate("C1") == "open_gate_auto_healthcheck_failed"
