"""The two MCP servers in `apps/aire-server/mcp/` (#55), end to end on a dev box.

Every tool call travels the real door — the FastAPI app, the local Postgres, the
engine with a Codex turn (`fake_codex.py`: the model is the only fake) — through
an adapter that stands in for urllib and nothing else. So a file pushed by `sync`
is read back by `read_document`, found by the persona's own `rag_store` mid-turn,
and the turn it answered in is read back by `read_chat`: both ends, each through
the path the product uses."""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mcp"))

import aire_gate  # noqa: E402
import aire_stdio  # noqa: E402
import persona_mcp  # noqa: E402
import projects_mcp  # noqa: E402
import sync  # noqa: E402

from aire.engine.core import WORKSPACES  # noqa: E402

TOKEN = "the-owners-own-door-token"
FAKE = str(Path(__file__).with_name("fake_codex.py"))
EXPEDIENTE = "# Sources — golf\n\n\n## Verified\n\n- El club Atlas tiene 391,400 metros cubicos al año.\n"


@pytest.fixture()
def door(monkeypatch, tmp_path):
    import aire.bearer
    import aire.door
    from aire.deps import drop_engine

    monkeypatch.setattr(aire.bearer, "ACCEPTED_TOKENS", (TOKEN,))
    monkeypatch.setattr(aire.door, "ACCEPTED_TOKENS", (TOKEN,))
    for name, value in (("AIRE_CODEX_COMMAND", json.dumps([sys.executable, FAKE])),
                        ("FAKE_CODEX_STORE", str(tmp_path / "codex")), ("CODEX_HOME", str(tmp_path / "codex"))):
        monkeypatch.setenv(name, value)
    drop_engine()
    from aire.server import app

    project = f"mcp-{uuid.uuid4().hex[:8]}"
    with TestClient(app, raise_server_exceptions=False) as client:
        yield project, _http(client), _stream(client)
        _http(client)("DELETE", f"/projects/{project}/corpus/research")
    drop_engine()
    shutil.rmtree(WORKSPACES / project, ignore_errors=True)


def _http(client):
    def call(method, path, body=None, query=None, raw=False):
        resp = client.request(method, path, json=body, params=query,
                              headers={"authorization": f"Bearer {TOKEN}"})
        if resp.status_code >= 400:
            raise aire_gate.GateError(f"{resp.status_code} {resp.text}")
        return resp.text if raw else resp.json()
    return call


def _stream(client):
    def stream(method, path, body):
        resp = client.request(method, path, json=body, headers={"authorization": f"Bearer {TOKEN}"})
        return aire_gate.parse_sse(resp.text.splitlines())
    return stream


def _tools(http, stream):
    return {t.name: t for t in projects_mcp.tools(http) + persona_mcp.tools(http, stream)}


def _call(table, name, **args):
    out = aire_stdio.call_tool(table, {"name": name, "arguments": args})
    assert not out["isError"], out["content"][0]["text"]
    text = out["content"][0]["text"]
    return json.loads(text) if text[:1] in "[{" else text


def test_a_pushed_tree_reads_back_exactly_and_a_repush_changes_nothing(door, tmp_path):
    project, http, stream = door
    tree = tmp_path / "corpus"
    (tree / "casos" / "golf").mkdir(parents=True)
    (tree / "casos" / "golf" / "sources-golf.md").write_text(EXPEDIENTE, encoding="utf-8")
    (tree / "casos" / "golf" / "folio.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
    base = f"/projects/{project}/corpus/research"
    first = sync.push(tree, base, "corpus/", http)
    assert first["changed"] == ["corpus/casos/golf/sources-golf.md"]
    assert first["skipped"] == ["casos/golf/folio.png (binary)"]
    assert sync.push(tree, base, "corpus/", http)["changed"] == []
    tools = _tools(http, stream)
    read = _call(tools, "read_document", project=project, corpus_id="research",
                 doc_id="corpus/casos/golf/sources-golf.md")
    assert read["text"] == EXPEDIENTE
    back = tmp_path / "pulled"
    assert sync.pull(back, base, "corpus/", http)["written"] == ["corpus/casos/golf/sources-golf.md"]
    assert (back / "casos/golf/sources-golf.md").read_text(encoding="utf-8") == EXPEDIENTE


def test_write_search_and_history_through_the_projects_tools(door):
    project, http, stream = door
    tools = _tools(http, stream)
    common = {"project": project, "corpus_id": "research", "doc_id": "corpus/backlog.md"}
    _call(tools, "write_document", **common, text="Idea: el pozo del club, sin verificar.")
    _call(tools, "write_document", **common, text="Idea: el pozo del club, verificada en el Atlas.")
    hits = _call(tools, "search_documents", project=project, corpus_id="research", query="pozo verificada")
    assert hits and hits[0]["doc_id"] == "corpus/backlog.md"
    versions = _call(tools, "document_history", **common)["versions"]
    assert len(versions) == 2
    old = _call(tools, "read_document", **common, version=versions[-1]["version"])
    assert "sin verificar" in old["text"]
    assert {"corpus_id": "research", "docs": 1} == {k: v for k, v in _call(
        tools, "list_corpora", project=project)["corpora"][0].items() if k in ("corpus_id", "docs")}


def test_the_persona_reads_its_expediente_resumes_and_the_chat_reads_back(door):
    project, http, stream = door
    tools = _tools(http, stream)
    _call(tools, "write_document", project=project, corpus_id="research",
          doc_id="corpus/casos/golf/sources-golf.md", text=EXPEDIENTE)
    turn = {"project": project, "session": "guion-golf", "provider": "codex", "tools": ["rag_store"]}
    first = _call(tools, "ask_persona", **turn, message="search: research club Atlas metros")
    assert "391,400" in first["reply"] and first["tools_used"] == ["rag_store/search_documents"]
    again = _call(tools, "ask_persona", **turn, message="sigue")
    assert again["reply"].endswith("after 1"), "the same session resumed the same thread"
    chats = _call(tools, "list_chats", project=project)["sessions"]
    assert [c["provider"] for c in chats] == ["codex"]
    said = _call(tools, "read_chat", project=project, session="guion-golf")["turns"]
    assert [t["role"] for t in said] == ["user", "assistant", "user", "assistant"]
    assert said[0]["text"] == "search: research club Atlas metros"


def test_a_corpus_binding_is_added_only_when_the_persona_can_search():
    with_rag = persona_mcp.turn_body({"message": "hola", "tools": ["rag_store"], "corpus_id": "research"})
    assert with_rag["message"].startswith("[Project corpus: `research`.") and with_rag["tools"] == ["rag_store"]
    bare = persona_mcp.turn_body({"message": "hola", "tools": [], "corpus_id": "research"})
    assert bare["message"] == "hola" and "tools" not in bare


def test_a_tool_failure_is_the_agents_to_read_never_the_servers_death():
    def down(*_a, **_k):
        raise aire_gate.GateError("503 the database is down")
    tools = {t.name: t for t in projects_mcp.tools(down)}
    out = aire_stdio.call_tool(tools, {"name": "list_documents", "arguments": {"project": "p", "corpus_id": "c"}})
    assert out["isError"] and "503" in out["content"][0]["text"]
    reply = aire_stdio.handle("aire-projects", tools, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert {t["name"] for t in reply["result"]["tools"]} >= {"read_document", "list_chats", "read_chat"}


def test_the_token_file_may_be_raw_or_an_env_line(tmp_path, monkeypatch):
    path = tmp_path / "token.txt"
    monkeypatch.setenv("AIRE_TOKEN_FILE", str(path))
    path.write_text("OTHER=x\nAIRE_AUTH_TOKEN=abc123\n", encoding="utf-8")
    assert aire_gate.token() == "abc123"
    path.write_text("raw-token\n", encoding="utf-8")
    assert aire_gate.token() == "raw-token"
    monkeypatch.setenv("AIRE_GATE_URL", "http://evil.example")
    with pytest.raises(ValueError):
        aire_gate.gate_url()
