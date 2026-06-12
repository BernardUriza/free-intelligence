"""Fact extraction must work with ANY utility_call client — the real
LLMClient or a RunnerJudgeClient.

Regression for the 2026-05-20 finding: with LEGACY_LLM_ENABLED=false the
LLMClient.utility_call became a no-op (returned empty text), so the
automatic extraction safety net failed every turn
(`facts_extraction_failed: Expecting value: line 1 column 1`). stages.py
now injects a RunnerJudgeClient (OAuth Max via /v1/judge) when legacy is
off. These tests pin the duck-typed contract: extract_facts only needs
`.utility_call` returning an object with `.text` + `.stop_reason`.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from personas.insult.core.facts import extract_facts


@pytest.mark.asyncio
async def test_extract_facts_works_with_judge_like_client():
    """A RunnerJudgeClient-shaped client (returns a JudgeResponse-like obj
    with .text + .stop_reason) drives extraction end to end. This is the
    path that's live in prod now that the legacy LLMClient is disabled."""
    judge = SimpleNamespace()
    judge.utility_call = AsyncMock(
        return_value=SimpleNamespace(
            text='[{"fact": "Alex tiene lupus seronegativo en estudio", "category": "health"}]',
            stop_reason="end_turn",
        )
    )

    out = await extract_facts(
        judge,
        "claude-haiku-4-5-20251001",
        "Alex",
        [],
        [{"user_name": "Alex", "content": "tengo lupus seronegativo"}],
    )

    assert out == [{"fact": "Alex tiene lupus seronegativo en estudio", "category": "health"}]
    judge.utility_call.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_facts_empty_response_keeps_existing():
    """The exact failure shape of the dead LLMClient: utility_call returns
    empty text → json.loads raises → existing facts preserved, NOT wiped.
    A flaky extraction must never erase what the [REMEMBER:] marker path
    already saved."""
    dead = SimpleNamespace()
    dead.utility_call = AsyncMock(return_value=SimpleNamespace(text="", stop_reason="end_turn"))
    existing = [{"fact": "fact previo del marker path", "category": "general"}]

    out = await extract_facts(
        dead,
        "claude-haiku-4-5-20251001",
        "Alex",
        existing,
        [{"user_name": "Alex", "content": "hola"}],
    )

    assert out == existing


@pytest.mark.asyncio
async def test_extract_facts_transport_error_keeps_existing():
    """If the judge HTTP call raises (timeout / 5xx), extraction degrades
    gracefully to existing facts instead of crashing the background task."""
    import httpx

    flaky = SimpleNamespace()
    flaky.utility_call = AsyncMock(side_effect=httpx.ConnectTimeout("runner cold"))
    existing = [{"fact": "fact previo", "category": "general"}]

    out = await extract_facts(
        flaky,
        "claude-haiku-4-5-20251001",
        "Alex",
        existing,
        [{"user_name": "Alex", "content": "hola"}],
    )

    assert out == existing
