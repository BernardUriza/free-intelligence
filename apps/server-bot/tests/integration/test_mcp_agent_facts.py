"""MCP tools for `agent_facts` — the bot's self-knowledge (v4.20.14 PR-1).

These are the first WRITE-capable tools in the persona_memory MCP server, so the
tests cover both the happy path and the resistance cases that keep a malformed
call from ever touching Postgres:
  - every tool: the agent is the persona bound to the turn, never an argument
    (2026-09-26: a model-supplied agent_id let one persona rewrite another's).
  - get_agent_facts: optional category filter, formatting.
  - add_agent_fact: rejects an out-of-enum provenance BEFORE connecting.
  - update_agent_fact: needs fact_id, needs at least one field, soft-delete path.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from persona_runner import mcp_tools
from persona_runner.mcp_tools import shared
from persona_runner.mcp_tools.turn_context import bind_turn_principal, reset_turn_principal

_get = mcp_tools.get_agent_facts.handler
_add = mcp_tools.add_agent_fact.handler
_upd = mcp_tools.update_agent_fact.handler


class _FakeConn:
    """Records SQL it was asked to run and returns canned results."""

    def __init__(self, *, fetch=None, fetchval=None, execute="UPDATE 1"):
        self._fetch = fetch if fetch is not None else []
        self._fetchval = fetchval
        self._execute = execute
        self.calls: list[tuple] = []
        self.closed = False

    async def fetch(self, sql, *args):
        self.calls.append(("fetch", sql, args))
        return self._fetch

    async def fetchval(self, sql, *args):
        self.calls.append(("fetchval", sql, args))
        return self._fetchval

    async def execute(self, sql, *args):
        self.calls.append(("execute", sql, args))
        return self._execute

    async def close(self):
        self.closed = True


def _patch_conn(monkeypatch, conn):
    monkeypatch.setattr(shared, "_connect", AsyncMock(return_value=conn))


@pytest.fixture(autouse=True)
def _insult_turn():
    """Every call runs inside an Insult turn, bound by the server as in production."""
    token = bind_turn_principal(user_id="907264175246569543", channel_id="1489180895264116736", agent_id="insult")
    yield
    reset_turn_principal(token)


@pytest.fixture
def _unbound_persona():
    token = bind_turn_principal(user_id="907264175246569543", channel_id="1489180895264116736", agent_id="")
    yield
    reset_turn_principal(token)


# ─── the persona is bound by the server, never named by the model ───────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        lambda: _get({}),
        lambda: _add({"fact": "x", "provenance": "self_declared"}),
        lambda: _upd({"fact_id": 5, "fact": "x"}),
        lambda: _upd({"fact_id": 5, "delete": True}),
    ],
)
async def test_every_tool_refuses_a_turn_with_no_persona_bound(monkeypatch, _unbound_persona, call):
    spy = AsyncMock()
    monkeypatch.setattr(shared, "_connect", spy)
    out = await call()
    spy.assert_not_awaited()
    assert "no persona bound" in repr(out).lower()


@pytest.mark.parametrize("tool", [mcp_tools.get_agent_facts, mcp_tools.add_agent_fact, mcp_tools.update_agent_fact])
def test_no_tool_lets_the_model_name_the_agent(tool):
    assert "agent_id" not in tool.input_schema


@pytest.mark.asyncio
async def test_a_model_supplied_agent_id_is_ignored_on_write(monkeypatch):
    conn = _FakeConn(fetchval=3)
    _patch_conn(monkeypatch, conn)
    await _add({"agent_id": "alice", "fact": "soy ALICE", "provenance": "self_declared"})
    assert conn.calls[0][2][0] == "insult"


@pytest.mark.asyncio
async def test_another_personas_fact_cannot_be_rewritten_or_deleted(monkeypatch):
    # The row exists but belongs to ALICE: scoped by agent_id, Postgres matches nothing.
    conn = _FakeConn(execute="UPDATE 0")
    _patch_conn(monkeypatch, conn)
    edited = await _upd({"fact_id": 11, "fact": "ALICE ahora es cruel"})
    deleted = await _upd({"fact_id": 11, "delete": True})
    assert "no active self-fact" in repr(edited).lower()
    assert "no active self-fact" in repr(deleted).lower()
    for _kind, sql, args in conn.calls:
        assert "agent_id = $" in sql
        assert args[-1] == "insult"


# ─── get_agent_facts ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_agent_facts_lists_facts(monkeypatch):
    conn = _FakeConn(
        fetch=[
            {"id": 7, "category": "voice", "fact": "soy abrasivo", "provenance": "self_declared", "updated_at": 1.0},
        ]
    )
    _patch_conn(monkeypatch, conn)
    out = await _get({})
    blob = repr(out)
    assert "soy abrasivo" in blob
    assert "self_declared" in blob
    # No category filter → the WHERE clause must not include category.
    sql = conn.calls[0][1]
    assert "category = $2" not in sql
    assert conn.closed


@pytest.mark.asyncio
async def test_get_agent_facts_category_filter(monkeypatch):
    conn = _FakeConn(fetch=[])
    _patch_conn(monkeypatch, conn)
    await _get({"category": "voice"})
    sql, args = conn.calls[0][1], conn.calls[0][2]
    assert "category = $2" in sql
    assert args == ("insult", "voice")


@pytest.mark.asyncio
async def test_get_agent_facts_empty(monkeypatch):
    _patch_conn(monkeypatch, _FakeConn(fetch=[]))
    out = await _get({})
    assert "no self-facts" in repr(out).lower()


# ─── add_agent_fact ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_agent_fact_rejects_bad_provenance_before_db(monkeypatch):
    spy = AsyncMock()
    monkeypatch.setattr(shared, "_connect", spy)
    out = await _add({"fact": "x", "category": "voice", "provenance": "invented"})
    spy.assert_not_awaited()  # never reached Postgres
    assert "provenance" in repr(out).lower()


@pytest.mark.asyncio
async def test_add_agent_fact_requires_fact(monkeypatch):
    spy = AsyncMock()
    monkeypatch.setattr(shared, "_connect", spy)
    out = await _add({"fact": "", "provenance": "self_declared"})
    spy.assert_not_awaited()
    assert "required" in repr(out).lower()


@pytest.mark.asyncio
async def test_add_agent_fact_inserts(monkeypatch):
    conn = _FakeConn(fetchval=42)
    _patch_conn(monkeypatch, conn)
    out = await _add({"fact": "no me disculpo", "category": "voice", "provenance": "self_declared"})
    assert "42" in repr(out)
    kind, sql, args = conn.calls[0]
    assert kind == "fetchval"
    assert "INSERT INTO agent_facts" in sql
    assert args == ("insult", "no me disculpo", "voice", "self_declared")


@pytest.mark.asyncio
async def test_add_agent_fact_defaults_category(monkeypatch):
    conn = _FakeConn(fetchval=1)
    _patch_conn(monkeypatch, conn)
    await _add({"fact": "f", "provenance": "user_attributed"})
    assert conn.calls[0][2][2] == "general"


# ─── update_agent_fact ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_requires_fact_id(monkeypatch):
    spy = AsyncMock()
    monkeypatch.setattr(shared, "_connect", spy)
    out = await _upd({"fact": "x"})
    spy.assert_not_awaited()
    assert "fact_id" in repr(out).lower()


@pytest.mark.asyncio
async def test_update_nothing_to_change(monkeypatch):
    spy = AsyncMock()
    monkeypatch.setattr(shared, "_connect", spy)
    out = await _upd({"fact_id": 5})
    spy.assert_not_awaited()
    assert "nothing to update" in repr(out).lower()


@pytest.mark.asyncio
async def test_update_bad_provenance(monkeypatch):
    spy = AsyncMock()
    monkeypatch.setattr(shared, "_connect", spy)
    out = await _upd({"fact_id": 5, "provenance": "nope"})
    spy.assert_not_awaited()
    assert "provenance" in repr(out).lower()


@pytest.mark.asyncio
async def test_update_sets_fields(monkeypatch):
    conn = _FakeConn(execute="UPDATE 1")
    _patch_conn(monkeypatch, conn)
    out = await _upd({"fact_id": 5, "fact": "nuevo", "category": "identity"})
    assert "5" in repr(out)
    sql, args = conn.calls[0][1], conn.calls[0][2]
    assert "fact = $1" in sql and "category = $2" in sql
    assert "updated_at = extract(epoch from now())" in sql
    assert "agent_id = $4" in sql
    assert args == ("nuevo", "identity", 5, "insult")


@pytest.mark.asyncio
async def test_update_soft_delete(monkeypatch):
    conn = _FakeConn(execute="UPDATE 1")
    _patch_conn(monkeypatch, conn)
    out = await _upd({"fact_id": 9, "delete": True})
    assert "soft-deleted" in repr(out).lower()
    sql, args = conn.calls[0][1], conn.calls[0][2]
    assert "deleted_at = extract(epoch from now())" in sql
    assert "agent_id = $2" in sql and args == (9, "insult")


@pytest.mark.asyncio
async def test_update_missing_row_errors(monkeypatch):
    conn = _FakeConn(execute="UPDATE 0")
    _patch_conn(monkeypatch, conn)
    out = await _upd({"fact_id": 999, "fact": "x"})
    assert "no active self-fact" in repr(out).lower()
