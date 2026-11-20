"""The voice lane: real lines for register, drawn at random, never on a fragile turn.

Mutator rule: positive (the block reaches a normal turn, the lines closest to the
ask are dropped) + resistance (a serious or vulnerable turn never fetches it, a
full guidance drops it whole, a dead lane is a normal turn).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from persona_core import guidance as guidance_mod
from persona_core.corpus import style


class _Conn:
    def __init__(self, rows):
        self.rows = rows
        self.closed = False

    async def fetch(self, *_args):
        return self.rows

    async def close(self):
        self.closed = True


def _rows(similarities):
    return [{"id": i, "chunk_text": f"linea {i}", "similarity": s} for i, s in enumerate(similarities)]


@pytest.fixture
def pool(monkeypatch):
    def _set(similarities):
        conn = _Conn(_rows(similarities))
        monkeypatch.setattr(style, "embed_query", AsyncMock(return_value=[0.0] * 384))
        monkeypatch.setattr(style, "connect", AsyncMock(return_value=conn))
        return conn

    return _set


async def test_lines_closest_to_the_ask_are_dropped(pool):
    """POSITIVE: near-duplicates of the query are the ones the model copies."""
    conn = pool([0.95, 0.80, 0.94, 0.81, 0.93, 0.82, 0.83])
    lines = await style.draw_style_lines("no mames", namespace="__style_insult__")
    assert [d["id"] for d in lines] == [1, 3, 5, 6]
    assert conn.closed


async def test_small_pool_keeps_every_line(pool):
    pool([0.95, 0.80])
    lines = await style.draw_style_lines("no mames", namespace="__style_insult__")
    assert [d["id"] for d in lines] == [0, 1]


async def test_block_wraps_lines_and_logs_their_ids(pool):
    pool([0.8, 0.7])
    with patch.object(style.log, "info") as info:
        block = await style.build_style_block("qué pedo", namespace="__style_insult__", header="CÓMO HABLA")
    assert (
        block
        == "CÓMO HABLA\n<voice_examples>\n<example>linea 0</example>\n<example>linea 1</example>\n</voice_examples>"
    )
    call = next(c for c in info.call_args_list if c.args[0] == "style_exemplars_used")
    assert call.kwargs["ids"] == [0, 1]


async def test_dead_lane_is_none_and_warns(monkeypatch):
    monkeypatch.setattr(style, "embed_query", AsyncMock(return_value=None))
    with patch.object(style.log, "warning") as warning:
        assert await style.build_style_block("qué pedo", namespace="__style_insult__", header="H") is None
    assert warning.call_args.args[0] == "style_lane_unavailable"


async def _guidance(message, provider, monkeypatch, *, guidance="PRESET"):
    monkeypatch.setattr(guidance_mod, "load_user_facts", AsyncMock(return_value=[]))
    monkeypatch.setattr(guidance_mod, "build_turn_guidance", lambda **_: guidance)
    return await guidance_mod.guidance_for_turn(
        memory=None,
        user_id="u",
        current_message=message,
        recent_messages=[],
        persona_id="insult",
        voice_examples=provider,
    )


async def test_normal_turn_gets_the_block_before_the_preset(monkeypatch):
    provider = AsyncMock(return_value="VOZ")
    out = await _guidance("oye qué opinas del deploy de hoy", provider, monkeypatch)
    assert out == "VOZ\n\nPRESET"


async def test_crisis_turn_never_fetches_the_block(monkeypatch):
    """RESISTANCE: the safety overlay must not compete with vulgar examples."""
    provider = AsyncMock(return_value="VOZ")
    out = await _guidance("me quiero morir, ya no aguanto nada", provider, monkeypatch)
    provider.assert_not_awaited()
    assert out == "PRESET"


async def test_block_is_dropped_whole_when_guidance_is_full(monkeypatch):
    full = "x" * (guidance_mod.MAX_GUIDANCE_CHARS - 5)
    out = await _guidance("oye qué opinas del deploy", AsyncMock(return_value="VOZ VOZ"), monkeypatch, guidance=full)
    assert out == full


async def test_provider_fault_is_a_normal_turn(monkeypatch):
    out = await _guidance("oye qué opinas del deploy", AsyncMock(side_effect=RuntimeError), monkeypatch)
    assert out == "PRESET"
