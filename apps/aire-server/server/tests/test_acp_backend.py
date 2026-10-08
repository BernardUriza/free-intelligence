"""The ACP backend, end to end over real stdio: a fake agent (`fake_acp_agent.py`)
on the other side of the pipe, `drain` on this side, and the mirror in the local
Postgres between them. Every assertion here is about the seam the native path
never had to cross: an agent that mints its own session id, replays history on
load, and reports no cost unless it chooses to."""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

from aire import acp_mirror, db
from aire.agent_sdk import Birth, backend_for, build_options, providers
from aire.agent_sdk.claude import project_key_for_directory
from aire.engine.contract import TurnSpec
from aire.engine.drain import drain
from aire.engine.vision import send_turn

FAKE = str(Path(__file__).with_name("fake_acp_agent.py"))


@pytest.fixture
def roster(monkeypatch, tmp_path):
    store = tmp_path / "agent-memory"
    monkeypatch.setenv("AIRE_ACP_AGENTS", json.dumps(
        {"fake": {"command": [sys.executable, FAKE], "env": {"FAKE_ACP_STORE": str(store)}}}))
    return store


def _birth(tmp_path: Path, session: str, mode: str = "agent") -> Birth:
    return Birth(None, "p", str(tmp_path), session, TurnSpec(mode=mode, provider="fake"), False)


async def _turn(birth: Birth, text: str) -> list[dict]:
    async with backend_for("fake").client(build_options(birth)) as client:
        await send_turn(client, text, ())
        return [event async for event in drain(client)]


def _result(events):
    return next(e["result"] for e in events if e["type"] == "result")


async def _rows(cwd: Path, session: str) -> list:
    async with db.acquire() as conn:
        return await conn.fetch(
            "SELECT kind, agent_session, entry FROM aire_agent_log"
            " WHERE project_key = $1 AND session_id = $2 AND provider = 'fake' ORDER BY seq",
            project_key_for_directory(str(cwd)), session)


@pytest.mark.anyio
async def test_a_turn_streams_text_and_lands_in_the_mirror(roster, tmp_path):
    session = str(uuid.uuid4())
    events = await _turn(_birth(tmp_path, session), "hola")
    assert [e["text"] for e in events if e["type"] == "text"] == ["pong: ", "hola"]
    result = _result(events)
    assert result.text == "pong: hola" and result.subtype == "success" and result.model == "fake"
    assert result.usage == {"input_tokens": 3, "output_tokens": 2,
                            "cache_read_input_tokens": 1, "cache_creation_input_tokens": 0}
    kinds = [r["kind"] for r in await _rows(tmp_path, session)]
    assert kinds == ["session", "prompt", "AgentMessageChunk", "AgentMessageChunk", "result"]


@pytest.mark.anyio
async def test_agent_mode_allows_a_tool_and_complete_mode_rejects_it(roster, tmp_path):
    allowed = _result(await _turn(_birth(tmp_path, str(uuid.uuid4())), "use a tool"))
    assert [(t.name, t.is_error) for t in allowed.tool_calls] == [("fake_tool", False)]
    assert allowed.answer == "pong: use a tool"
    rejected = _result(await _turn(_birth(tmp_path, str(uuid.uuid4()), "complete"), "use a tool"))
    assert [(t.name, t.is_error) for t in rejected.tool_calls] == [("fake_tool", True)]


@pytest.mark.anyio
async def test_a_warm_resume_loads_the_agents_memory_without_replaying_it(roster, tmp_path):
    session = str(uuid.uuid4())
    await _turn(_birth(tmp_path, session), "one")
    events = await _turn(_birth(tmp_path, session), "two")
    # the replayed "pong: one" never reaches drain: only this turn's chunks do
    assert [e["text"] for e in events if e["type"] == "text"] == ["pong: ", "two"]
    rows = await _rows(tmp_path, session)
    assert [r["kind"] for r in rows].count("session") == 1  # loaded, not re-minted
    assert (await acp_mirror.agent_session(project_key_for_directory(str(tmp_path)), session, "fake")
            == rows[0]["agent_session"])


@pytest.mark.anyio
async def test_a_cold_resume_opens_a_fresh_session_and_says_so(roster, tmp_path):
    session = str(uuid.uuid4())
    await _turn(_birth(tmp_path, session), "one")
    shutil.rmtree(roster)  # the box forgot: the agent's disk memory is gone
    events = await _turn(_birth(tmp_path, session), "two")
    assert _result(events).text == "pong: two"
    sessions = [json.loads(r["entry"]) for r in await _rows(tmp_path, session) if r["kind"] == "session"]
    assert len(sessions) == 2 and sessions[1]["replaced"] == sessions[0]["agent_session"]


@pytest.mark.anyio
async def test_a_reported_cost_reaches_the_result(roster, tmp_path):
    result = _result(await _turn(_birth(tmp_path, str(uuid.uuid4())), "what does it cost"))
    assert result.usage["total_cost_usd"] == pytest.approx(0.0042)


def test_the_roster_names_the_providers(roster):
    assert providers() == ("claude", "fake")


@pytest.mark.anyio
async def test_the_engine_answers_exists_for_an_acp_session(roster, tmp_path, monkeypatch):
    from aire.engine.core import Engine
    monkeypatch.setattr("aire.engine.core.WORKSPACES", tmp_path.parent)
    engine, session = Engine(session_store=None), str(uuid.uuid4())
    assert await engine.has_session(tmp_path.name, session, "fake") is False
    await _turn(_birth(tmp_path, session), "one")
    assert await engine.has_session(tmp_path.name, session, "fake") is True
