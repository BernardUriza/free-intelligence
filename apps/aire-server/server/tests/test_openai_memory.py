"""A routed key on the OpenAI door remembers without a Codex turn (#54), over real sockets.

Both ends ride the product's own paths: the correction is a Codex turn's prompt row
(the backend `stop-judge-correct.py` reaches through the message door, fake model,
real `CodexClient` mirror), the verdict goes through the door to the fake Azure, and
the rows are read from `aire_agent_log`. An unrouted key is proven byte-for-byte."""

import asyncio
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx
import pytest

import fake_upstream
from test_openai_gateway import doors, invited  # noqa: F401 — fixtures

from aire import db, openai_memory
from aire.agent_sdk import backend_for, build_options
from aire.agent_sdk.base import Birth
from aire.engine import Engine, core, memory_tool
from aire.engine.contract import TurnSpec
from aire.engine.drain import drain
from aire.engine.vision import send_turn
from aire.keys import sdk_session_uuid

FAKE = str(Path(__file__).with_name("fake_codex.py"))
RAW = b'{"model":"gpt-5.4-mini",  "temperature":0,"messages":[{"role":"system","content":"rubric"},' \
      b'{"role":"user","content":"judge this close"}]}'


def _correction(denied: str, said: str) -> str:
    """The exact shape `claude-commands/hooks/stop-judge-correct.py` sends (its `message()`)."""
    return ("CORRECTION FROM BERNARD, the human you judge for, of one of your Stop verdicts.\n"
            f"When: 2026-11-12T20:00:00Z. Claude session: s1. Repo: /r.\nWhat you denied: {denied}\n"
            f"His correction: {said}\nThis is the record later verdicts must recall: judge a similar "
            "close by this correction. Reply with one line: OK, recorded.")


@pytest.fixture
def casita(monkeypatch, tmp_path):
    project = f"judge-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    monkeypatch.setenv("AIRE_CODEX_COMMAND", json.dumps([sys.executable, FAKE]))
    monkeypatch.setenv("FAKE_CODEX_STORE", str(tmp_path / "codex-home"))
    return project


def _route(monkeypatch, nickname, project):
    conf = {**json.loads(openai_memory.ROUTES_FILE.read_text()), "routes": {nickname: project}}
    monkeypatch.setattr(openai_memory, "content", lambda: conf)


async def _codex_turn(project: str, session: str, text: str) -> None:
    birth = Birth(None, project, str(Engine._cwd(project)), sdk_session_uuid(session),
                  TurnSpec(mode="complete", provider="codex"), False)
    async with backend_for("codex").client(build_options(birth)) as client:
        await send_turn(client, text, ())
        [_ async for _ in drain(client)]


def _send(url, body, key):
    return httpx.post(f"{url}/openai/v1/chat/completions", content=body, timeout=30,
                      headers={"authorization": f"Bearer {key}", "content-type": "application/json"})


async def _rows(project_key: str) -> list:
    async with db.acquire() as conn:
        return await conn.fetch("SELECT kind, session_id, entry FROM aire_agent_log WHERE project_key = $1"
                                " AND provider = 'openai' ORDER BY seq", project_key)


def test_an_unrouted_key_is_relayed_byte_for_byte(doors, invited):
    invited.holder("aire_plain")
    assert _send(doors.aire, RAW, "aire_plain").status_code == 200
    assert fake_upstream.state["body"] == RAW


def test_a_routed_key_reads_corrections_and_remembers_the_verdict(doors, invited, casita, monkeypatch):
    asyncio.run(_codex_turn(casita, "corrections", _correction("a close with no receipt", "the PR link was the receipt")))
    nick = invited.holder("aire_judge")
    _route(monkeypatch, nick, casita)
    assert _send(doors.aire, RAW, "aire_judge").status_code == 200
    system = json.loads(fake_upstream.state["body"])["messages"][0]["content"]
    assert system.startswith("rubric\n\nCorrections Bernard made")
    assert "denied: a close with no receipt | Bernard: the PR link was the receipt" in system
    key = Engine.session_key(casita, datetime.now(openai_memory.MEXICO_CITY).strftime("%Y-%m-%d"))
    route = openai_memory.route_for(nick)
    assert (route.project_key, route.session_id) == (key["project_key"], key["session_id"]), "the message door's key"
    rows = []
    for _ in range(50):
        rows = asyncio.run(_rows(key["project_key"]))
        if len(rows) == 2:
            break
        time.sleep(0.1)
    assert [r["kind"] for r in rows] == ["request", "response"]
    assert json.loads(rows[0]["entry"])["text"] == "judge this close", "the caller's words, not the injected block"
    assert json.loads(rows[1]["entry"])["text"] == "pong"


def test_a_verdict_that_quotes_a_correction_is_not_one(casita):
    project_key = Engine.session_key(casita, "d")["project_key"]
    asyncio.run(_codex_turn(casita, "d", "the user pasted: CORRECTION FROM BERNARD ..."))
    assert asyncio.run(memory_tool.marked(project_key, "CORRECTION FROM BERNARD", 10, 1000)) == []


def test_a_slow_memory_relays_the_body_unchanged(doors, invited, casita, monkeypatch):
    async def stalled(*_):
        await asyncio.sleep(10)

    monkeypatch.setattr(memory_tool, "marked", stalled)
    _route(monkeypatch, invited.holder("aire_slow"), casita)
    started = time.monotonic()
    assert _send(doors.aire, RAW, "aire_slow").status_code == 200
    assert time.monotonic() - started < 4
    assert fake_upstream.state["body"] == RAW
