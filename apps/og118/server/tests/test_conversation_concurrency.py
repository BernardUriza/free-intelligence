"""CONV-CONCURRENCY-1 — a stale device must not be able to lose a pin.

Every conversation mutation used to travel as a whole-record PUT, so the last
writer won the WHOLE record. Pin a chat on the phone, then send a message from
the desktop whose in-memory copy predates the pin, and the desktop's persist
rewrites the record without `pinnedAt`. The pin is gone. Nothing failed, nothing
was logged, and no message was lost — only the organization flags, silently.

The fix is not a version check. `updatedAt` could not have carried one anyway:
pinning deliberately does NOT stamp `updatedAt` (organization must not fake
recency in the active list), so an optimistic guard comparing `updatedAt` would
see no change and wave the clobbering write through. On top of that, `updatedAt`
is minted by the client, and two devices do not share a clock.

So the authority moved instead: a PUT no longer carries an opinion about the
flags — the server keeps its own — and the only way to move them is PATCH, which
sends the delta rather than the world. A device cannot drop a flag it is not
allowed to speak about.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app as app_module
from conversations import ConversationStore


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def conversation_store(tmp_path):
    store = ConversationStore(tmp_path / "conversations")
    app_module.app.dependency_overrides[app_module.get_conversation_store] = lambda: store
    yield store
    app_module.app.dependency_overrides.pop(app_module.get_conversation_store, None)


def _record(cid: str, **over) -> dict:
    record = {
        "id": cid,
        "title": "Hola",
        "createdAt": "2026-08-22T00:00:00Z",
        "updatedAt": "2026-08-22T00:00:00Z",
        "messages": [{"role": "user", "content": "hola", "timestamp": "2026-08-22T00:00:00Z"}],
        "preview": "hola",
        "schemaVersion": 1,
    }
    record.update(over)
    return record


# --- the race itself -------------------------------------------------------


def test_a_stale_put_cannot_lose_a_pin(client):
    """The founding scenario, end to end."""
    client.put("/conversations/conv-uno", json=_record("conv-uno"))
    # Device A (phone) pins.
    assert client.patch(
        "/conversations/conv-uno", json={"pinnedAt": "2026-08-22T10:00:00Z"}
    ).status_code == 200

    # Device B (desktop) sends a message. Its copy of the record predates the
    # pin, so its whole-record put simply has no `pinnedAt` in it.
    stale = _record(
        "conv-uno",
        updatedAt="2026-08-22T11:00:00Z",
        messages=[
            {"role": "user", "content": "hola", "timestamp": "2026-08-22T00:00:00Z"},
            {"role": "user", "content": "otra", "timestamp": "2026-08-22T11:00:00Z"},
        ],
    )
    assert client.put("/conversations/conv-uno", json=stale).status_code == 200

    after = client.get("/conversations/conv-uno").json()
    assert after["pinnedAt"] == "2026-08-22T10:00:00Z", "the stale device dropped the pin"
    # And the content the stale device DID own still landed.
    assert len(after["messages"]) == 2
    assert after["updatedAt"] == "2026-08-22T11:00:00Z"


def test_a_stale_put_cannot_lose_an_archive(client):
    client.put("/conversations/conv-uno", json=_record("conv-uno"))
    client.patch("/conversations/conv-uno", json={"archivedAt": "2026-08-22T10:00:00Z"})

    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    assert client.get("/conversations/conv-uno").json()["archivedAt"] == "2026-08-22T10:00:00Z"


def test_a_stale_put_cannot_undo_a_rename(client):
    """The same bug wearing a different field's name.

    A rename sets `titleCustom`; the next message on another device carries the
    AUTO-derived title, which would overwrite it.
    """
    client.put("/conversations/conv-uno", json=_record("conv-uno"))
    client.patch(
        "/conversations/conv-uno", json={"title": "Presupuesto", "titleCustom": True}
    )

    client.put("/conversations/conv-uno", json=_record("conv-uno", title="hola"))

    after = client.get("/conversations/conv-uno").json()
    assert after["title"] == "Presupuesto"
    assert after["titleCustom"] is True


def test_an_auto_title_still_updates_when_there_was_no_rename(client):
    """The preservation must not freeze titles that were never customized."""
    client.put("/conversations/conv-uno", json=_record("conv-uno", title="hola"))

    client.put("/conversations/conv-uno", json=_record("conv-uno", title="otra cosa"))

    assert client.get("/conversations/conv-uno").json()["title"] == "otra cosa"


def test_a_stale_put_cannot_refile_a_conversation(client):
    """`projectId` is birth-only; a put that forgot it must not un-file the chat."""
    client.put("/conversations/conv-uno", json=_record("conv-uno", projectId="proj-1"))

    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    assert client.get("/conversations/conv-uno").json()["projectId"] == "proj-1"


# --- PATCH semantics -------------------------------------------------------


def test_an_omitted_key_leaves_its_field_alone(client):
    client.put("/conversations/conv-uno", json=_record("conv-uno"))
    client.patch("/conversations/conv-uno", json={"pinnedAt": "2026-08-22T10:00:00Z"})

    client.patch("/conversations/conv-uno", json={"title": "Otro", "titleCustom": True})

    assert client.get("/conversations/conv-uno").json()["pinnedAt"] == "2026-08-22T10:00:00Z"


def test_an_explicit_null_clears_the_field(client):
    """The distinction a whole-record put cannot express."""
    client.put("/conversations/conv-uno", json=_record("conv-uno"))
    client.patch("/conversations/conv-uno", json={"pinnedAt": "2026-08-22T10:00:00Z"})

    response = client.patch("/conversations/conv-uno", json={"pinnedAt": None})

    assert response.status_code == 200
    assert "pinnedAt" not in response.json()
    assert "pinnedAt" not in client.get("/conversations/conv-uno").json()


def test_patch_returns_the_merged_record(client):
    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    body = client.patch(
        "/conversations/conv-uno", json={"pinnedAt": "2026-08-22T10:00:00Z"}
    ).json()

    assert body["id"] == "conv-uno"
    assert body["pinnedAt"] == "2026-08-22T10:00:00Z"
    assert body["messages"], "the caller syncs from this; it must be the whole record"


def test_patching_a_missing_conversation_is_404(client):
    assert client.patch("/conversations/conv-nope", json={"pinnedAt": None}).status_code == 404


def test_an_empty_patch_is_rejected(client):
    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    response = client.patch("/conversations/conv-uno", json={})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EMPTY_PATCH"


def test_a_null_title_is_rejected(client):
    """A conversation always has a title; reverting a rename sends the DERIVED
    one, never a clear."""
    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    response = client.patch("/conversations/conv-uno", json={"title": None})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TITLE_REQUIRED"


def test_an_invalid_id_is_rejected_before_touching_a_path(client):
    assert client.patch("/conversations/..%2Fescape", json={"pinnedAt": None}).status_code in (404, 422)


# --- isolation -------------------------------------------------------------


def test_another_account_cannot_patch_your_conversation(client, as_account):
    as_account("acct-A")
    client.put("/conversations/conv-uno", json=_record("conv-uno"))

    as_account("acct-B")
    response = client.patch("/conversations/conv-uno", json={"pinnedAt": "2026-08-22T10:00:00Z"})

    # 404, never 403: a foreign id must be indistinguishable from a missing one.
    assert response.status_code == 404

    as_account("acct-A")
    assert "pinnedAt" not in client.get("/conversations/conv-uno").json()


def test_a_first_put_still_creates_the_record(client):
    """put_content reads before it writes; a brand-new conversation has nothing
    to read and must still land."""
    response = client.put("/conversations/conv-nueva", json=_record("conv-nueva"))

    assert response.status_code == 200
    assert client.get("/conversations/conv-nueva").json()["id"] == "conv-nueva"
