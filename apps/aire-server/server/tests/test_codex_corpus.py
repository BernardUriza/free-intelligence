"""`rag_store` for the Codex backend (#55): a Codex persona searches its project's
documents mid-turn. Both ends are the product's: the document lands through
`corpus.put` (what the door and the projects MCP call), and `codex exec` (fake
model, real argv) spawns the stdio server the `-c` overrides declare."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest

from aire import corpus, db
from aire.agent_sdk import backend_for, build_options
from aire.agent_sdk.base import Birth
from aire.engine.contract import TurnSpec
from aire.engine.drain import drain
from aire.engine.vision import send_turn

FAKE = str(Path(__file__).with_name("fake_codex.py"))


@pytest.fixture
def box(monkeypatch, tmp_path):
    store = tmp_path / "codex-home"
    monkeypatch.setenv("AIRE_CODEX_COMMAND", json.dumps([sys.executable, FAKE]))
    monkeypatch.setenv("FAKE_CODEX_STORE", str(store))
    return store


async def _turn(cwd: Path, text: str, tools=("rag_store",)):
    birth = Birth(None, cwd.name, str(cwd), str(uuid.uuid4()),
                  TurnSpec(mode="complete", provider="codex", tools=tuple(tools)), False)
    async with backend_for("codex").client(build_options(birth)) as client:
        await send_turn(client, text, ())
        events = [event async for event in drain(client)]
    return next(e["result"] for e in events if e["type"] == "result")


@pytest.mark.anyio
async def test_a_codex_persona_finds_its_projects_expediente(box, tmp_path):
    casita = tmp_path / f"vp-{uuid.uuid4().hex[:6]}"
    casita.mkdir()
    await corpus.put(casita.name, "exp", "casos/golf/sources-golf.md",
                     "El club Atlas tiene concesionados 391,400 metros cubicos al año.")
    try:
        result = await _turn(casita, "search: exp concesion del club Atlas")
    finally:
        await corpus.drop(casita.name, "exp")
        await db.close()
    assert "391,400" in result.text and "sources-golf.md" in result.text
    assert [(t.name, t.is_error) for t in result.tool_calls] == [("rag_store/search_documents", False)]


@pytest.mark.anyio
async def test_another_casitas_shelf_is_out_of_reach(box, tmp_path):
    mine, theirs = tmp_path / "mine-vp", tmp_path / "theirs-vp"
    mine.mkdir(), theirs.mkdir()
    word = f"tamarindo{uuid.uuid4().hex[:6]}"
    await corpus.put(mine.name, "exp", "a.md", f"La palabra es {word}.")
    try:
        result = await _turn(theirs, f"search: exp {word}")
    finally:
        await corpus.drop(mine.name, "exp")
        await db.close()
    assert word not in result.text.replace(f"search: exp {word}", "")
    assert "No document" in result.text


@pytest.mark.anyio
async def test_codex_mounts_rag_store_and_memory_together(box, tmp_path):
    casita = tmp_path / "both-vp"
    casita.mkdir()
    await _turn(casita, "hola", tools=("rag_store", "memory"))
    argv = json.loads((box / "last_argv.json").read_text())
    names = {a.split(".")[1] for a in argv if a.startswith("mcp_servers.")}
    assert names == {"rag_store", "memory"}
    assert 'mcp_servers.rag_store.default_tools_approval_mode="approve"' in argv
