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
    assert result.usage == {"input_tokens": 3, "output_tokens": 2, "cache_read_input_tokens": 7,
                            "cache_creation_input_tokens": 1, "total_cost_usd": result.usage["total_cost_usd"]}
    assert result.usage["total_cost_usd"] > 0, "tokens priced at list (#53), nominal on a plan seat"
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


def _env(box: Path) -> dict:
    return json.loads((box / "last_env.json").read_text())


@pytest.mark.anyio
async def test_the_slot_env_reaches_the_process_and_a_plan_turn_is_priced_nominal(box, tmp_path):
    """#53: the rotor's slot rides on top of the daemon's environ into `codex
    exec`; the turn's tokens are priced at list so a metered key can bank."""
    birth = Birth(None, "p", str(tmp_path), str(uuid.uuid4()),
                  TurnSpec(mode="complete", provider="codex"), False,
                  credential_env={"CODEX_API_KEY": "sk-test", "CODEX_HOME": str(box)}, metered=True)
    result = _result(await _turn(birth, "hola"))
    assert _env(box) == {"CODEX_HOME": str(box), "CODEX_API_KEY": "sk-test"}
    assert result.usage["total_cost_usd"] > 0, "tokens priced at OpenAI list for the plan model"
    assert result.error is None


@pytest.mark.anyio
async def test_a_plan_at_its_limit_rotates_to_the_metered_key_and_banks_it(box, tmp_path, monkeypatch, capsys):
    """The whole #53 acceptance through `run_turn`: the plan seat answers
    `turn.failed` with the limit wording, the rotor cools `codex/oauth/primary`
    LOUDLY, the retry rides `codex/apikey/fallback` with `CODEX_API_KEY` in the
    process, and the turn lands in `aire_spend` as metered."""
    import aire.engine.core as core
    import aire.engine.turn as turn_mod
    from aire.engine.credentials import Rotor
    from aire.engine.core import Engine

    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    banked: list[tuple[float, bool]] = []

    async def fake_bank(door, project, session, holder, usd, metered=True, tokens=None):
        banked.append((usd, metered))

    monkeypatch.setattr(turn_mod.spend, "bank", fake_bank)
    engine = Engine(session_store=object())
    engine.rotor = Rotor({"CODEX_HOME": str(box), "CODEX_API_KEY_FALLBACK": "sk-fallback"})
    spec = TurnSpec(mode="complete", provider="codex")
    events = [e async for e in engine.run_stream("proj", str(uuid.uuid4()), "limit please", spec)]
    assert [e["type"] for e in events] == ["text", "result"], f"the lying attempt leaked: {events}"
    assert _result(events).text == "pong: limit please"
    assert engine.rotor.cooling_names() == ["codex/oauth/primary"]
    assert "CREDENTIAL-EXHAUSTED codex/oauth/primary" in capsys.readouterr().out
    assert _env(box)["CODEX_API_KEY"] == "sk-fallback"
    assert banked and banked[-1][1] is True and banked[-1][0] > 0, "the fallback turn is metered"
    engine.rotor.burn("codex/apikey/fallback")
    dry = [e async for e in engine.run_stream("proj", str(uuid.uuid4()), "hola", spec)]
    assert [e.get("error") for e in dry] == ["credentials_exhausted"] and dry[0]["provider"] == "codex"
    await engine.aclose()


def test_the_box_names_the_provider_and_the_roster_cannot_take_the_name(box, monkeypatch):
    assert providers() == ("claude", "codex")
    monkeypatch.setenv("AIRE_ACP_AGENTS", json.dumps({"codex": ["codex-acp"]}))
    with pytest.raises(BadRoster):
        roster()
    monkeypatch.delenv("AIRE_ACP_AGENTS")
    monkeypatch.delenv("AIRE_CODEX_COMMAND")
    assert providers() == ("claude",)


@pytest.mark.anyio
async def test_the_casita_persona_reaches_codex_as_agents_md(box, tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Astra\nYou write scripts.\n", encoding="utf-8")
    await _turn(_birth(tmp_path, str(uuid.uuid4())), "hola")
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# Astra\nYou write scripts."
    argv = _argv(box)
    assert "project_doc_max_bytes=1048576" in argv
    (tmp_path / "CLAUDE.md").unlink()
    await _turn(_birth(tmp_path, str(uuid.uuid4())), "hola")
    assert not (tmp_path / "AGENTS.md").exists()
