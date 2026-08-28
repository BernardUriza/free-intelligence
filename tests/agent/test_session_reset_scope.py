"""Channel reset must reach EVERY persona's casita in the channel — and say
whether it was durable.

The recovery need predates the AIRE route (2026-05-19: a failed tool call left
a session convinced the tool did not exist for as long as the session lived; on
2026-07-14 a reset that missed the sibling personas left a stuck Vultur session
poisoned in silence). On the AIRE route the session is the TOPIC, so the reset
drops the channel's durable topic rows and clears the RAM mirrors — the next
turn of each casita mints a fresh topic and folds history anew.

Positive: every casita of the channel resets. Resistance: another channel's
casitas are never touched, an idle channel is a no-op that doesn't raise, and a
reset Postgres could not make durable REPORTS itself as such instead of
impersonating one that held.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from persona_runner.engine import aire_route, aire_topic


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    monkeypatch.setattr(aire_route, "_casita_state", aire_route._casita_state.__class__())


def _seed(casita: str, topic_id: str) -> aire_route.CasitaState:
    state = aire_route.casita_state(casita)
    state.topic = aire_topic.TopicMemory(topic_id=topic_id, last_activity=100.0, answered=True)
    return state


@pytest.mark.asyncio
async def test_reset_clears_every_persona_of_the_channel(monkeypatch):
    insult = _seed("insult-C1", "t1")
    vultur = _seed("vultur-C1", "t2")
    monkeypatch.setattr(aire_topic, "reset_channel", AsyncMock(return_value=["insult-C1", "vultur-C1"]))

    result = await aire_route.reset_channel("C1")

    assert result["durable"] is True
    assert result["casitas"] == ["insult-C1", "vultur-C1"]
    assert insult.topic.topic_id == "" and insult.topic.answered is False
    assert vultur.topic.topic_id == "" and vultur.topic.answered is False


@pytest.mark.asyncio
async def test_reset_never_touches_another_channels_casitas(monkeypatch):
    _seed("insult-C1", "t1")
    other = _seed("insult-C2", "t9")
    monkeypatch.setattr(aire_topic, "reset_channel", AsyncMock(return_value=["insult-C1"]))

    result = await aire_route.reset_channel("C1")

    assert "insult-C2" not in result["casitas"]
    assert other.topic.topic_id == "t9" and other.topic.answered is True


@pytest.mark.asyncio
async def test_resetting_an_idle_channel_is_a_noop_that_does_not_raise(monkeypatch):
    monkeypatch.setattr(aire_topic, "reset_channel", AsyncMock(return_value=[]))

    result = await aire_route.reset_channel("nobody-home")

    assert result == {"durable": True, "casitas": []}


@pytest.mark.asyncio
async def test_a_reset_postgres_could_not_hold_reports_itself_as_not_durable(monkeypatch):
    """None from the durable half means the reset lives only in this process's
    RAM — a restart loses it, and equating it with a durable one would be the
    autosave-ACK lie (verify-before-assuming Rule 19)."""
    ram = _seed("insult-C1", "t1")
    monkeypatch.setattr(aire_topic, "reset_channel", AsyncMock(return_value=None))

    result = await aire_route.reset_channel("C1")

    assert result["durable"] is False
    assert result["casitas"] == ["insult-C1"]
    assert ram.topic.topic_id == ""  # the RAM half still reset
