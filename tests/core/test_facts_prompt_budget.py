"""Extraction-payload budget + per-user save serialization (2026-07-20).

Bug A: a whale user's COMPLETE fact set (3,345 facts / 300K chars in prod)
exceeded JudgeRequest's 256K `user_text` cap → HTTP 422 on every extraction →
the user's facts frozen forever (Bernard, frozen since the 07-14 purga).
`extract_facts` now budgets the existing-facts and conversation sections,
newest-first, so the payload is bounded no matter how much a user accumulates.

Bug B: two personas extracting the same user concurrently race their
DELETE+reinsert snapshots into `idx_pf_auto_dedup` and one save dies whole
(Alex's save, 2026-07-20 19:05Z). The per-user lock serializes the
read-merge-save cycle within the gateway process.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from persona_core.facts import (
    CONVERSATION_CHAR_BUDGET,
    EXISTING_FACTS_CHAR_BUDGET,
    extract_facts,
)
from persona_gateway.facts import FactExtractor


class _CapturingJudge:
    def __init__(self, reply: str = "[]"):
        self.reply = reply
        self.calls: list[list[dict]] = []

    async def utility_call(self, system_prompt, messages, *, model=None, max_tokens=4096):
        self.calls.append(messages)
        return SimpleNamespace(text=self.reply, stop_reason="end_turn")


@pytest.mark.asyncio
async def test_whale_fact_set_is_budgeted_under_judge_cap():
    judge = _CapturingJudge()
    facts = [{"fact": f"hecho número {i} " + "x" * 80, "category": "general"} for i in range(4000)]
    await extract_facts(judge, None, "bernard2389", facts, [{"user_name": "b", "content": "hola"}])
    user_text = judge.calls[0][0]["content"]
    assert len(user_text) < 256_000
    assert len(user_text) < EXISTING_FACTS_CHAR_BUDGET + CONVERSATION_CHAR_BUDGET + 1_000
    assert "hecho número 0 " in user_text
    assert "hecho número 3999 " not in user_text


@pytest.mark.asyncio
async def test_small_fact_set_passes_through_complete():
    judge = _CapturingJudge()
    facts = [{"fact": f"dato {i}", "category": "general"} for i in range(20)]
    await extract_facts(judge, None, "alex", facts, [{"user_name": "a", "content": "hola"}])
    user_text = judge.calls[0][0]["content"]
    for i in range(20):
        assert f"dato {i}" in user_text


@pytest.mark.asyncio
async def test_giant_paste_keeps_newest_messages():
    judge = _CapturingJudge()
    messages = [
        {"user_name": "u", "content": "PASTE " + "z" * (CONVERSATION_CHAR_BUDGET + 10_000)},
        {"user_name": "u", "content": "mensaje reciente importante"},
    ]
    await extract_facts(judge, None, "u", [], messages)
    user_text = judge.calls[0][0]["content"]
    assert "mensaje reciente importante" in user_text
    assert len(user_text) < 256_000


class _OverlapMemory:
    """Records how many extraction cycles hold the critical section at once."""

    def __init__(self):
        self.active = 0
        self.max_active = 0

    async def get_facts(self, user_id):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        return []

    async def get_auto_facts(self, user_id):
        await asyncio.sleep(0.01)
        return []

    async def save_facts(self, user_id, facts):
        await asyncio.sleep(0.01)
        self.active -= 1


def _extractor(memory) -> FactExtractor:
    return FactExtractor(SimpleNamespace(persona_id="insult"), memory, set())


@pytest.mark.asyncio
async def test_concurrent_same_user_extractions_serialize():
    memory = _OverlapMemory()
    judge = _CapturingJudge(reply='[{"fact": "es dev", "category": "general"}]')
    ext = _extractor(memory)
    turn = [{"user_name": "u", "content": "soy dev"}]
    await asyncio.gather(
        ext._extract_and_persist(judge, "same-user", "u", turn),
        ext._extract_and_persist(judge, "same-user", "u", turn),
    )
    assert memory.max_active == 1


@pytest.mark.asyncio
async def test_distinct_users_still_extract_concurrently():
    memory = _OverlapMemory()
    judge = _CapturingJudge(reply='[{"fact": "es dev", "category": "general"}]')
    ext = _extractor(memory)
    turn = [{"user_name": "u", "content": "soy dev"}]
    await asyncio.gather(
        ext._extract_and_persist(judge, "user-a", "u", turn),
        ext._extract_and_persist(judge, "user-b", "u", turn),
    )
    assert memory.max_active == 2
