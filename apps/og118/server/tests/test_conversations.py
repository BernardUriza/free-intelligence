"""Cloud conversation store — /conversations CRUD keyed by the auth principal.

The server counterpart of fi-glass's ConversationLibrary contract: an account's
sanitized transcripts persist server-side (one JSON per conversation) so they
follow the account across browsers. Ownership is structural (per-owner dir):
another account's id is indistinguishable from a missing one.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from conversations import ConversationStore, valid_conversation_id


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def conversation_store(tmp_path):
    store = ConversationStore(tmp_path / "conversations")
    app_module.app.dependency_overrides[app_module.get_conversation_store] = lambda: store
    yield store
    app_module.app.dependency_overrides.pop(app_module.get_conversation_store, None)


def _record(cid: str, *, title: str = "Hola", updated: str = "2026-07-08T00:00:00Z") -> dict:
    return {
        "id": cid,
        "title": title,
        "createdAt": "2026-07-08T00:00:00Z",
        "updatedAt": updated,
        "messages": [
            {"role": "user", "content": "hola", "timestamp": "2026-07-08T00:00:00Z"},
            {"role": "assistant", "content": "¡hola!", "timestamp": "2026-07-08T00:00:01Z"},
        ],
        "preview": "¡hola!",
        "schemaVersion": 1,
    }


def _put(client: TestClient, record: dict, **kw):
    return client.put(f"/conversations/{record['id']}", json=record, **kw)


def test_put_get_roundtrip(client: TestClient, as_account) -> None:
    record = _record("conv-1")
    assert _put(client, record).status_code == 200
    got = client.get("/conversations/conv-1")
    assert got.status_code == 200
    body = got.json()
    assert body["id"] == "conv-1"
    assert body["messages"] == record["messages"]
    assert body["preview"] == "¡hola!"


def test_list_returns_light_summaries_newest_first(client: TestClient, as_account) -> None:
    _put(client, _record("conv-old", updated="2026-07-01T00:00:00Z"))
    _put(client, _record("conv-new", updated="2026-07-08T00:00:00Z"))
    resp = client.get("/conversations")
    assert resp.status_code == 200
    convs = resp.json()["conversations"]
    assert [c["id"] for c in convs] == ["conv-new", "conv-old"]
    assert all("messages" not in c for c in convs)


def test_cross_account_isolation(client: TestClient, as_account) -> None:
    _put(client, _record("conv-a"))
    as_account("acct-B")
    assert client.get("/conversations/conv-a").status_code == 404
    assert client.get("/conversations").json()["conversations"] == []
    # B's delete of A's id is a no-op on A's data
    client.delete("/conversations/conv-a")
    as_account("acct-A")
    assert client.get("/conversations/conv-a").status_code == 200


def test_body_id_must_match_path_id(client: TestClient, as_account) -> None:
    record = _record("conv-x")
    resp = client.put("/conversations/conv-y", json=record)
    assert resp.status_code == 422
    assert client.get("/conversations/conv-x").status_code == 404
    assert client.get("/conversations/conv-y").status_code == 404


def test_invalid_id_rejected(client: TestClient, as_account) -> None:
    record = _record("bad.id")
    assert _put(client, record).status_code == 422
    assert valid_conversation_id("conv_1-ok")
    assert not valid_conversation_id("../escape")
    assert not valid_conversation_id("a/b")
    assert not valid_conversation_id("")
    assert not valid_conversation_id("x" * 65)


def test_delete_and_clear(client: TestClient, as_account) -> None:
    _put(client, _record("conv-1"))
    _put(client, _record("conv-2"))
    assert client.delete("/conversations/conv-1").status_code == 200
    assert client.get("/conversations/conv-1").status_code == 404
    # deleting a missing id is a quiet no-op (client contract parity)
    assert client.delete("/conversations/conv-1").status_code == 200
    cleared = client.delete("/conversations")
    assert cleared.status_code == 200
    assert cleared.json()["cleared"] == 1
    assert client.get("/conversations").json()["conversations"] == []


def test_oversized_conversation_rejected(client: TestClient, as_account) -> None:
    record = _record("conv-big")
    record["messages"] = [
        {"role": "user", "content": "x" * (app_module.MAX_CONVERSATION_BYTES + 1024)}
    ]
    assert _put(client, record).status_code == 413


def test_extra_top_level_fields_dropped(client: TestClient, as_account) -> None:
    record = _record("conv-1")
    record["accessToken"] = "Bearer hunter2"
    assert _put(client, record).status_code == 200
    assert "accessToken" not in client.get("/conversations/conv-1").json()


def test_upsert_replaces(client: TestClient, as_account) -> None:
    _put(client, _record("conv-1", title="v1"))
    _put(client, _record("conv-1", title="v2"))
    assert client.get("/conversations/conv-1").json()["title"] == "v2"
    assert len(client.get("/conversations").json()["conversations"]) == 1


def test_absurd_body_rejected_from_content_length_before_parsing(
    client: TestClient, as_account
) -> None:
    """The outer wall (MAX_REQUEST_BODY_BYTES): a body that DECLARES a size past
    the ceiling is refused from its header — the per-endpoint caps only run after
    FastAPI has materialized and parsed the whole body, which is exactly what a
    500 MB PUT must never get to do."""
    response = client.put(
        "/conversations/conv-1",
        content=b'{"nope":1}',
        headers={
            "content-type": "application/json",
            "content-length": str(app_module.MAX_REQUEST_BODY_BYTES + 1),
        },
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "REQUEST_TOO_LARGE"


def test_a_normal_body_passes_the_wall(client: TestClient, as_account) -> None:
    """The wall cuts the absurd, never the legitimate: a real record still saves."""
    assert _put(client, _record("conv-1")).status_code == 200


def test_pin_archive_flags_roundtrip_and_surface_in_summaries(
    client: TestClient, as_account
) -> None:
    """CONV-ORGANIZE-1: pinnedAt/archivedAt persist through the upsert and reach
    the sidebar's light summaries (the client organizes sections from them)."""
    pinned = _record("conv-pin")
    pinned["pinnedAt"] = "2026-07-13T00:00:00Z"
    archived = _record("conv-arch")
    archived["archivedAt"] = "2026-07-13T01:00:00Z"
    assert _put(client, pinned).status_code == 200
    assert _put(client, archived).status_code == 200

    assert client.get("/conversations/conv-pin").json()["pinnedAt"] == "2026-07-13T00:00:00Z"
    by_id = {c["id"]: c for c in client.get("/conversations").json()["conversations"]}
    assert by_id["conv-pin"]["pinnedAt"] == "2026-07-13T00:00:00Z"
    assert by_id["conv-arch"]["archivedAt"] == "2026-07-13T01:00:00Z"
    # Absent flags stay absent — summaries never carry null placeholders.
    assert "archivedAt" not in by_id["conv-pin"]
    assert "pinnedAt" not in by_id["conv-arch"]


def test_unpin_upsert_drops_the_stored_flag(client: TestClient, as_account) -> None:
    """Unpinning = the client re-puts the record WITHOUT the field; exclude_none
    must drop it from the stored JSON, not fossilize the old timestamp."""
    pinned = _record("conv-1")
    pinned["pinnedAt"] = "2026-07-13T00:00:00Z"
    assert _put(client, pinned).status_code == 200
    assert _put(client, _record("conv-1")).status_code == 200
    assert "pinnedAt" not in client.get("/conversations/conv-1").json()
    convs = client.get("/conversations").json()["conversations"]
    assert "pinnedAt" not in convs[0]
