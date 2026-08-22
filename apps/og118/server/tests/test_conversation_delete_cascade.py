"""Deleting a conversation must take the native session with it.

`DELETE /conversations/{id}` removed the record the user sees and left the SDK's
own transcript — tool_use and tool_result blocks included — alive in the session
store, addressable only by an id that had just been thrown away. A whole
conversation outliving its own deletion.

`DELETE /conversations` (the bulk clear) had the identical hole, and there the
residue multiplies by the entire account rather than by one chat.

The cascade is BEST EFFORT on purpose, mirroring the lifespan's posture: a dead
Postgres must never turn "delete my chat" into a 500 — the record is already
gone and the caller is owed that answer. What it must not do is fail silently.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from conversations import ConversationStore


class SpyRunner:
    """Stands in for the module-level runner: records the cascade, nothing else."""

    def __init__(self, *, explode: bool = False) -> None:
        self.forgotten: list[str] = []
        self.explode = explode

    async def forget_session(self, session_id: str) -> bool:
        self.forgotten.append(session_id)
        if self.explode:
            raise RuntimeError("postgres is down")
        return True


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def conversation_store(tmp_path):
    store = ConversationStore(tmp_path / "conversations")
    app_module.app.dependency_overrides[app_module.get_conversation_store] = lambda: store
    yield store
    app_module.app.dependency_overrides.pop(app_module.get_conversation_store, None)


@pytest.fixture
def spy(monkeypatch):
    runner = SpyRunner()
    monkeypatch.setattr(app_module, "_runner", runner)
    return runner


def _record(cid: str) -> dict:
    return {
        "id": cid,
        "title": "Hola",
        "createdAt": "2026-08-22T00:00:00Z",
        "updatedAt": "2026-08-22T00:00:00Z",
        "messages": [{"role": "user", "content": "hola", "timestamp": "2026-08-22T00:00:00Z"}],
        "preview": "hola",
        "schemaVersion": 1,
    }


def test_deleting_one_conversation_forgets_its_native_session(client, spy):
    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    assert client.delete("/conversations/conv-uno").status_code == 200
    assert spy.forgotten == ["conv-uno"], (
        "the record went but the native transcript under it stayed reachable to nobody"
    )


def test_clearing_the_account_forgets_every_native_session(client, spy):
    for cid in ("conv-uno", "conv-dos", "conv-tres"):
        client.put(f"/conversations/{cid}", json=_record(cid))

    response = client.delete("/conversations")

    assert response.status_code == 200
    assert response.json()["cleared"] == 3
    assert sorted(spy.forgotten) == ["conv-dos", "conv-tres", "conv-uno"], (
        "the bulk clear is where the orphan multiplies by the whole account"
    )


def test_a_dead_memory_layer_never_blocks_the_visible_delete(client, monkeypatch, caplog):
    monkeypatch.setattr(app_module, "_runner", SpyRunner(explode=True))
    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    with caplog.at_level("ERROR"):
        response = client.delete("/conversations/conv-uno")

    assert response.status_code == 200, "the record is already gone; the caller is owed that"
    assert client.get("/conversations/conv-uno").status_code == 404
    assert "orphan transcript" in caplog.text, "best effort, but never in silence"
