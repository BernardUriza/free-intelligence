"""`memory` for the Codex backend (#54), proven at both ends of the data path.

The write end is the product's own: a Codex turn mirrored by `acp_mirror` into
`aire_agent_log`, and a Claude turn's row in `claude_session_store`. The read end
is the product's own too: `codex exec` (fake model, real argv) spawns the stdio
server the `-c` overrides declare, with the scrubbed env codex gives it, and the
model's `recall` comes back through MCP. Nothing is inserted by hand into the
table the read searches except the Claude row, which no Codex turn can write."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest

from aire import db
from aire.agent_sdk import backend_for, build_options, project_key_for_directory
from aire.agent_sdk.base import Birth
from aire.engine.contract import TurnSpec
from aire.engine.drain import drain
from aire.engine.vision import send_turn
from aire.store import create_postgres_session_store

FAKE = str(Path(__file__).with_name("fake_codex.py"))


@pytest.fixture
def box(monkeypatch, tmp_path):
    store = tmp_path / "codex-home"
    monkeypatch.setenv("AIRE_CODEX_COMMAND", json.dumps([sys.executable, FAKE]))
    monkeypatch.setenv("FAKE_CODEX_STORE", str(store))
    return store


def _casita(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.mkdir()
    return path


def _birth(cwd: Path, tools=(), mode: str = "complete") -> Birth:
    return Birth(None, cwd.name, str(cwd), str(uuid.uuid4()),
                 TurnSpec(mode=mode, provider="codex", tools=tuple(tools)), False)


async def _result(birth: Birth, text: str):
    async with backend_for("codex").client(build_options(birth)) as client:
        await send_turn(client, text, ())
        events = [event async for event in drain(client)]
    return next(e["result"] for e in events if e["type"] == "result")


def _argv(box: Path) -> list[str]:
    return json.loads((box / "last_argv.json").read_text())


@pytest.mark.anyio
async def test_a_codex_casita_recalls_what_an_earlier_session_said(box, tmp_path):
    word = f"zanahoria-{uuid.uuid4().hex[:8]}"
    judge = _casita(tmp_path, "judge")
    await _result(_birth(judge), f"the secret word is {word}")
    result = await _result(_birth(judge, ["memory"]), f"recall: {word}")
    assert f"pong: the secret word is {word}" in result.text, "the earlier session's answer came back"
    assert [(t.name, t.is_error) for t in result.tool_calls] == [("memory/recall", False)]


@pytest.mark.anyio
async def test_recall_never_crosses_into_another_casita(box, tmp_path):
    word = f"pepino-{uuid.uuid4().hex[:8]}"
    await _result(_birth(_casita(tmp_path, "mine")), f"the secret word is {word}")
    result = await _result(_birth(_casita(tmp_path, "theirs"), ["memory"]), f"recall: {word}")
    assert "the secret word" not in result.text
    assert [(t.name, t.is_error) for t in result.tool_calls] == [("memory/recall", False)]


@pytest.mark.anyio
async def test_recall_from_codex_also_finds_the_claude_transcript(box, tmp_path):
    word = f"jitomate-{uuid.uuid4().hex[:8]}"
    casita = _casita(tmp_path, "both")
    store = await create_postgres_session_store(db.dsn())
    key = {"project_key": project_key_for_directory(str(casita)), "session_id": str(uuid.uuid4())}
    await store.append(key, [{"type": "assistant", "uuid": str(uuid.uuid4()), "text": f"claude said {word}"}])
    result = await _result(_birth(casita, ["memory"]), f"recall: {word}")
    assert f"claude said {word}" in result.text


@pytest.mark.anyio
async def test_the_overrides_name_the_secret_never_carry_it(box, tmp_path):
    await _result(_birth(_casita(tmp_path, "flags"), ["memory"]), "hola")
    argv = " ".join(_argv(box))
    assert 'mcp_servers.memory.default_tools_approval_mode="approve"' in argv
    assert '"AIRE_DATABASE_URL"' in argv and db.dsn() not in argv


@pytest.mark.anyio
async def test_no_tools_mounts_nothing_and_an_unsupported_one_is_loud(box, tmp_path, capsys):
    await _result(_birth(_casita(tmp_path, "bare")), "hola")
    assert not any(a.startswith("mcp_servers.") for a in _argv(box))
    await _result(_birth(_casita(tmp_path, "persona"), ["persona", "memory"]), "hola")
    names = {a.split(".")[1] for a in _argv(box) if a.startswith("mcp_servers.")}
    assert names == {"memory"} and "CODEX-TOOL-UNSUPPORTED" in capsys.readouterr().out
