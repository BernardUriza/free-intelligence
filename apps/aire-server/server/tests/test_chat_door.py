"""The chat door (#55): a project's chats as turns, written the way the product
writes them — the SDK store for a Claude turn, `acp_mirror` for a Codex one — and
read the way the projects MCP reads them."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from aire import acp_mirror, db, tokens, transcripts
from aire.keys import sdk_session_uuid
from aire.store import create_postgres_session_store

TOKEN = "the-owners-own-door-token"
AUTH = {"authorization": f"Bearer {TOKEN}"}


@pytest.fixture()
def client(monkeypatch):
    import aire.bearer
    import aire.door

    monkeypatch.setattr(aire.bearer, "ACCEPTED_TOKENS", (TOKEN,))
    monkeypatch.setattr(aire.door, "ACCEPTED_TOKENS", (TOKEN,))
    from aire.server import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        # After startup: the lifespan reloads the invited roster from the database.
        monkeypatch.setitem(tokens._by_hash, tokens.digest("guest-key"), tokens.Holder("guest", 5.0, 0.0))
        yield test_client


async def _write(project: str, word: str) -> tuple[str, str]:
    """One Codex chat and one Claude chat in `project`, through the product's writers."""
    key = transcripts.project_key(project)
    codex, claude = sdk_session_uuid(f"guion-{word}"), str(uuid.uuid4())
    await acp_mirror.append(key, codex, "codex", "thread-1", "prompt", {"text": f"escribe el guion {word}"})
    await acp_mirror.append(key, codex, "codex", "thread-1", "item.completed",
                            {"id": "i1", "type": "agent_message", "text": f"aquí va el guion {word}"})
    await acp_mirror.append(key, codex, "codex", "thread-1", "result", {"usd": 0.01})
    store = await create_postgres_session_store(db.dsn())
    await store.append({"project_key": key, "session_id": claude},
                       [{"type": "user", "uuid": str(uuid.uuid4()),
                         "message": {"role": "user", "content": [{"type": "text", "text": f"hola {word}"}]}}])
    await db.close()
    return codex, claude


def test_a_projects_chats_are_listed_and_read_as_turns(client):
    project, word = f"chats-{uuid.uuid4().hex[:8]}", uuid.uuid4().hex[:6]
    codex, claude = asyncio.run(_write(project, word))
    listed = client.get(f"/projects/{project}/sessions", headers=AUTH).json()["sessions"]
    assert {(s["session"], s["provider"]) for s in listed} == {(codex, "codex"), (claude, "claude")}
    turns = client.get(f"/projects/{project}/sessions/guion-{word}/transcript", headers=AUTH).json()["turns"]
    assert [(t["role"], t["text"]) for t in turns] == [
        ("user", f"escribe el guion {word}"), ("assistant", f"aquí va el guion {word}")]
    by_uuid = client.get(f"/projects/{project}/sessions/{claude}/transcript", headers=AUTH).json()["turns"]
    assert [(t["role"], t["text"]) for t in by_uuid] == [("user", f"hola {word}")]


async def _long_claude_chat(project: str) -> str:
    """Six spoken turns on the main thread, plus what must never come back: a tool
    result, a system entry and a subagent sidechain (`subpath`)."""
    key, session = transcripts.project_key(project), str(uuid.uuid4())
    store = await create_postgres_session_store(db.dsn())
    entries = [{"type": "user" if i % 2 == 0 else "assistant", "uuid": str(uuid.uuid4()),
                "message": {"role": "x", "content": [{"type": "text", "text": f"turno {i}"}]}} for i in range(6)]
    entries.insert(3, {"type": "user", "uuid": str(uuid.uuid4()), "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "x" * 5000}]}})
    entries.insert(1, {"type": "system", "uuid": str(uuid.uuid4()), "text": "arranque"})
    for entry in entries:  # one append per entry, so each has its own seq
        await store.append({"project_key": key, "session_id": session}, [entry])
    await store.append({"project_key": key, "session_id": session, "subpath": "subagents/agent-1"},
                       [{"type": "assistant", "uuid": str(uuid.uuid4()),
                         "message": {"role": "assistant", "content": [{"type": "text", "text": "sidechain"}]}}])
    await db.close()
    return session


def test_a_transcript_reads_only_the_last_spoken_turns_of_the_main_thread(client):
    """Review of #55: `limit` is applied in SQL (a long session is never loaded
    whole), and only spoken user/assistant text of the main thread comes back."""
    project = f"chats-{uuid.uuid4().hex[:8]}"
    session = asyncio.run(_long_claude_chat(project))
    path = f"/projects/{project}/sessions/{session}/transcript"
    every = client.get(path, headers=AUTH).json()["turns"]
    assert [t["text"] for t in every] == [f"turno {i}" for i in range(6)]
    tail = client.get(path, params={"limit": 2}, headers=AUTH).json()["turns"]
    assert [(t["role"], t["text"]) for t in tail] == [("user", "turno 4"), ("assistant", "turno 5")]
    listed = client.get(f"/projects/{project}/sessions", headers=AUTH).json()["sessions"]
    assert [s["entries"] for s in listed] == [8], "the sidechain is not counted as the chat"


def test_another_project_never_sees_these_chats(client):
    project, word = f"chats-{uuid.uuid4().hex[:8]}", uuid.uuid4().hex[:6]
    asyncio.run(_write(project, word))
    other = client.get(f"/projects/other-{word}/sessions", headers=AUTH).json()["sessions"]
    assert other == []
    turns = client.get(f"/projects/other-{word}/sessions/guion-{word}/transcript", headers=AUTH).json()
    assert turns["turns"] == []


def test_the_project_list_names_casitas_and_their_persona(client, tmp_path, monkeypatch):
    import aire.chat_door

    (tmp_path / "videopipe").mkdir()
    (tmp_path / "videopipe" / "CLAUDE.md").write_text("Eres Astra.", encoding="utf-8")
    (tmp_path / "probe").mkdir()
    monkeypatch.setattr(aire.chat_door, "WORKSPACES", tmp_path)
    projects = client.get("/projects", headers=AUTH).json()["projects"]
    assert projects == [{"project": "probe", "persona": False}, {"project": "videopipe", "persona": True}]


def test_an_invited_key_or_nobody_cannot_read_chats(client):
    guest = {"authorization": "Bearer guest-key"}
    for path in ("/projects", "/projects/videopipe/sessions", "/projects/videopipe/sessions/x/transcript"):
        assert client.get(path, headers=guest).status_code == 403
        assert client.get(path).status_code == 401
