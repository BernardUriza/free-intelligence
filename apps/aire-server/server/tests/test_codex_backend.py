"""The Codex backend (#52) against a real `codex exec --json` process whose
model is fake: the argv dial, the memory (warm resume, cold resume LOUD), the
failure shapes, the modes sandbox, the weights per turn and images as files."""

from __future__ import annotations

import base64
import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest

from aire import acp_mirror, db
from aire.agent_sdk import backend_for, build_options, project_key_for_directory, providers
from aire.agent_sdk.acp_roster import BadRoster, roster
from aire.agent_sdk.base import Birth
from aire.engine.contract import TurnSpec
from aire.engine.drain import drain
from aire.engine.vision import send_turn

FAKE = str(Path(__file__).with_name("fake_codex.py"))
PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\0" * 16).decode()


@pytest.fixture
def box(monkeypatch, tmp_path):
    store = tmp_path / "codex-home"
    monkeypatch.setenv("AIRE_CODEX_COMMAND", json.dumps([sys.executable, FAKE]))
    monkeypatch.setenv("FAKE_CODEX_STORE", str(store))
    return store


def _birth(tmp_path: Path, session: str, mode: str = "agent", model: str | None = None) -> Birth:
    return Birth(None, "p", str(tmp_path), session,
                 TurnSpec(mode=mode, provider="codex", model=model), False)


async def _turn(birth: Birth, text: str, attachments=()) -> list[dict]:
    async with backend_for("codex").client(build_options(birth)) as client:
        await send_turn(client, text, attachments)
        return [event async for event in drain(client)]


def _result(events):
    return next(e["result"] for e in events if e["type"] == "result")


def _argv(box: Path) -> list[str]:
    return json.loads((box / "last_argv.json").read_text())


async def _rows(cwd: Path, session: str) -> list:
    async with db.acquire() as conn:
        return await conn.fetch(
            "SELECT kind, agent_session, entry FROM aire_agent_log"
            " WHERE project_key = $1 AND session_id = $2 AND provider = 'codex' ORDER BY seq",
            project_key_for_directory(str(cwd)), session)


@pytest.mark.anyio
async def test_a_turn_streams_text_banks_tokens_and_lands_in_the_mirror(box, tmp_path):
    session = str(uuid.uuid4())
    events = await _turn(_birth(tmp_path, session), "hola")
    assert [e["text"] for e in events if e["type"] == "text"] == ["pong: hola"]
    result = _result(events)
    assert result.text == "pong: hola" and result.subtype == "success" and result.model == "gpt-6-astra"
    assert result.usage == {"input_tokens": 3, "output_tokens": 2,
                            "cache_read_input_tokens": 7, "cache_creation_input_tokens": 1}
    assert [r["kind"] for r in await _rows(tmp_path, session)] == ["prompt", "session", "item.completed", "result"]
    argv = _argv(box)
    assert argv[:2] == ["exec", "-m"] and "resume" not in argv and "--json" in argv
    assert 'sandbox_mode="workspace-write"' in argv and 'approval_policy="never"' in argv


@pytest.mark.anyio
async def test_complete_mode_is_read_only_and_a_tool_fails_there(box, tmp_path):
    allowed = _result(await _turn(_birth(tmp_path, str(uuid.uuid4())), "use a tool"))
    assert [(t.name, t.is_error) for t in allowed.tool_calls] == [("command_execution", False)]
    rejected = _result(await _turn(_birth(tmp_path, str(uuid.uuid4()), "complete"), "use a tool"))
    assert [(t.name, t.is_error) for t in rejected.tool_calls] == [("command_execution", True)]
    assert 'sandbox_mode="read-only"' in _argv(box)


@pytest.mark.anyio
async def test_a_warm_resume_continues_the_thread_the_mirror_remembers(box, tmp_path):
    session = str(uuid.uuid4())
    await _turn(_birth(tmp_path, session), "one")
    events = await _turn(_birth(tmp_path, session), "two")
    assert _result(events).text == "pong: two after 1"
    rows = await _rows(tmp_path, session)
    sessions = [r for r in rows if r["kind"] == "session"]
    assert len(sessions) == 1  # continued, not re-minted
    thread = sessions[0]["agent_session"]
    assert _argv(box)[1:3] == ["resume", thread]
    assert await acp_mirror.agent_session(project_key_for_directory(str(tmp_path)), session, "codex") == thread


@pytest.mark.anyio
async def test_a_cold_resume_opens_a_fresh_thread_and_says_so(box, tmp_path, capsys):
    session = str(uuid.uuid4())
    await _turn(_birth(tmp_path, session), "one")
    shutil.rmtree(box)  # the box forgot: ~/.codex is gone
    events = await _turn(_birth(tmp_path, session), "two")
    assert _result(events).text == "pong: two"
    assert "CODEX-RESUME-LOST" in capsys.readouterr().out
    sessions = [json.loads(r["entry"]) for r in await _rows(tmp_path, session) if r["kind"] == "session"]
    assert len(sessions) == 2 and sessions[1]["replaced"] == sessions[0]["agent_session"]


@pytest.mark.anyio
async def test_a_failed_turn_and_a_silent_exit_are_error_results_never_text(box, tmp_path, capsys):
    failed = _result(await _turn(_birth(tmp_path, str(uuid.uuid4())), "fail"))
    assert failed.subtype == "error_turn_failed" and failed.text == ""
    crashed = _result(await _turn(_birth(tmp_path, str(uuid.uuid4())), "crash"))
    assert crashed.subtype == "error_exit_3" and crashed.text == ""
    out = capsys.readouterr().out
    assert "CODEX-TURN-FAILED" in out and "CODEX-EXIT" in out and "segfault" in out


@pytest.mark.anyio
async def test_the_turn_picks_the_weights_and_images_ride_as_files(box, tmp_path):
    image = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}
    result = _result(await _turn(_birth(tmp_path, str(uuid.uuid4()), model="gpt-6.1-sol"), "mira", (image,)))
    assert result.text == "pong: mira images: 1" and result.model == "gpt-6.1-sol"
    argv = _argv(box)
    assert argv[argv.index("-m") + 1] == "gpt-6.1-sol"
    assert argv[argv.index("-i") + 1].endswith("image-0.png")


def test_the_box_names_the_provider_and_the_roster_cannot_take_the_name(box, monkeypatch):
    assert providers() == ("claude", "codex")
    monkeypatch.setenv("AIRE_ACP_AGENTS", json.dumps({"codex": ["codex-acp"]}))
    with pytest.raises(BadRoster):
        roster()
    monkeypatch.delenv("AIRE_ACP_AGENTS")
    monkeypatch.delenv("AIRE_CODEX_COMMAND")
    assert providers() == ("claude",)
