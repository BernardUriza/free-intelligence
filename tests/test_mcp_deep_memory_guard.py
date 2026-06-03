"""The deep_memory MCP tool must never serve a reserved synthetic namespace.

`deep_memory` takes `user_id` as a free argument the agent supplies. Two
synthetic namespaces live in `deep_memory_chunks` alongside real users:
  - `__chatgpt_archive__` — Bernard's intimate ChatGPT history (health,
    sexuality, sensitive) routed OUT of auto-recall by the hybrid privacy
    choice (2026-06-03). It exists in the BDD for sovereignty, but must NEVER
    surface in a turn.
  - `__corpus_film__` — shared film-theory knowledge with its own path.

If the agent (by drift or a crafted message) passed one of these as `user_id`,
it would read data that must stay out of any public channel. The guard rejects
any `__`-prefixed id before it reaches `query_user_memory`.

Mutator rule: positive (legit Discord id still works) + resistance (each
reserved namespace is blocked, and the underlying query is never even run).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from insult.agent import mcp_tools

_handler = mcp_tools.deep_memory.handler


@pytest.mark.asyncio
@pytest.mark.parametrize("reserved", ["__chatgpt_archive__", "__corpus_film__", "__anything__"])
async def test_reserved_namespace_is_blocked_before_query(reserved, monkeypatch):
    spy = AsyncMock(return_value=[])
    monkeypatch.setattr("insult.core.deep_memory.query_user_memory", spy)

    out = await _handler({"user_id": reserved, "query": "lo que sea"})

    # The query must never run for a reserved namespace.
    spy.assert_not_awaited()
    # And the response says why (in-tool error, not a silent empty result).
    blob = repr(out).lower()
    assert "reserved namespace" in blob


@pytest.mark.asyncio
async def test_real_discord_id_still_reaches_query(monkeypatch):
    spy = AsyncMock(return_value=[])
    monkeypatch.setattr("insult.core.deep_memory.query_user_memory", spy)

    await _handler({"user_id": "907264175246569543", "query": "cine de autor"})

    spy.assert_awaited_once()
    assert spy.await_args.kwargs["user_id"] == "907264175246569543"


@pytest.mark.asyncio
async def test_missing_user_id_still_errors(monkeypatch):
    spy = AsyncMock(return_value=[])
    monkeypatch.setattr("insult.core.deep_memory.query_user_memory", spy)

    out = await _handler({"user_id": "", "query": "x"})
    spy.assert_not_awaited()
    assert "required" in repr(out).lower()
