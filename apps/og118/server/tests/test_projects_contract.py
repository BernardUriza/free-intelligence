"""The four data-contract gaps that blocked FIGLASS-PROJECTS-PAGE-1.

The Projects page needs things the server never said:

1. a project was `{id, name, createdAt, ownerId}` bare — the card renders a
   description and sorts by "Updated X ago", and neither existed;
2. no way to LIST a corpus over HTTP, so the knowledge rail had nothing to draw;
3. no capacity figure, so the meter had no denominator;
4. conversations carried no `projectId`, so a project could not list its own
   chats — the corpus binding was ephemeral, sent per request and stored nowhere.

Ownership is tested alongside each one: a non-owner must get the same answer as
"missing" (404, never 403 — no existence probing).
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

import app as app_module
from conversations import ConversationStore
from fi_runner.rag_store import RagStoreClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def store(monkeypatch, tmp_path):
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "contract.h5"))
    rag = RagStoreClient()
    app_module.app.dependency_overrides[app_module.get_rag_store] = lambda: rag
    yield rag
    app_module.app.dependency_overrides.pop(app_module.get_rag_store, None)


@pytest.fixture(autouse=True)
def conversation_store(tmp_path):
    """A conversation store per test. Without this the module-level default leaks
    records between tests and a filter assertion passes on the wrong data."""
    store = ConversationStore(tmp_path / "conversations")
    app_module.app.dependency_overrides[app_module.get_conversation_store] = lambda: store
    yield store
    app_module.app.dependency_overrides.pop(app_module.get_conversation_store, None)


@pytest.fixture(autouse=True)
def account(as_account):
    """Every test here runs as a REAL account, not the legacy bearer principal —
    ownership is the invariant under test and the bearer path bypasses it."""
    return as_account


def _create(client: TestClient, name: str = "P", **body) -> dict:
    resp = client.post("/projects", json={"name": name, **body})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _conversation(cid: str, *, project_id: str | None = None) -> dict:
    record = {
        "id": cid,
        "title": "Hola",
        "createdAt": "2026-08-22T00:00:00Z",
        "updatedAt": "2026-08-22T00:00:00Z",
        "messages": [{"role": "user", "content": "hola", "timestamp": "2026-08-22T00:00:00Z"}],
        "preview": "hola",
        "schemaVersion": 1,
    }
    if project_id is not None:
        record["projectId"] = project_id
    return record


# --- Gap 2: the project record ------------------------------------------------


def test_a_new_project_carries_description_instructions_and_updated_at(client):
    created = _create(client, "Papelería", description="precios y proveedores")["project"]

    assert created["description"] == "precios y proveedores"
    assert created["instructions"] == ""
    assert created["updatedAt"] == created["createdAt"], (
        "a project nobody has touched was updated exactly when it was created"
    )


def test_patch_edits_one_field_and_leaves_the_others_alone(client):
    pid = _create(client, "P", description="original")["project_id"]

    patched = client.patch(f"/projects/{pid}", json={"instructions": "responde en español"})

    assert patched.status_code == 200
    project = patched.json()["project"]
    assert project["instructions"] == "responde en español"
    assert project["description"] == "original", "an omitted field must not be wiped"
    assert project["name"] == "P"


def test_patch_with_an_empty_string_clears_the_field(client):
    pid = _create(client, "P", description="ya no aplica")["project_id"]

    project = client.patch(f"/projects/{pid}", json={"description": ""}).json()["project"]

    assert project["description"] == "", "omitted means leave alone; empty means clear"


def test_patch_moves_updated_at_because_it_is_the_index_sort_key(client):
    created = _create(client, "P")["project"]

    project = client.patch(f"/projects/{created['id']}", json={"name": "P2"}).json()["project"]

    assert project["updatedAt"] > created["updatedAt"], (
        "an edit that did not move updatedAt leaves the grid claiming it is older than it is"
    )


def test_a_legacy_project_without_the_new_fields_is_backfilled_on_read(client):
    """A project minted before this contract must not hand the grid a missing
    sort key — updatedAt falls back to createdAt, the only honest answer."""
    registry = app_module.app.dependency_overrides[app_module.get_project_registry]()
    registry._save(
        {
            "project-legacy": {
                "id": "project-legacy",
                "name": "viejo",
                "createdAt": "2026-01-01T00:00:00Z",
                "ownerId": "acct-A",
            }
        }
    )

    project = client.get("/projects/project-legacy").json()["project"]

    assert project["updatedAt"] == "2026-01-01T00:00:00Z", (
        "nothing has touched it since it was created — that is the only honest answer"
    )
    assert project["description"] == ""
    assert project["instructions"] == ""
    assert registry.list_for("acct-A")[0]["updatedAt"] == "2026-01-01T00:00:00Z", (
        "the grid sorts on this field, so the LIST path must backfill it too"
    )


def test_get_one_project_is_404_when_it_does_not_exist(client):
    assert client.get("/projects/project-nope").status_code == 404
    assert client.patch("/projects/project-nope", json={"name": "x"}).status_code == 404


# --- Gaps 1 + 3: documents and capacity ---------------------------------------


def test_documents_lists_the_corpus_with_its_capacity(client):
    pid = _create(client, "P")["project_id"]
    client.post(
        f"/projects/{pid}/upload",
        files={"file": ("precios.md", io.BytesIO(b"Lamina diez pesos. " * 40), "text/markdown")},
    )

    body = client.get(f"/projects/{pid}/documents").json()

    assert [d["docId"] for d in body["documents"]] == ["precios.md"]
    assert body["documents"][0]["chunks"] >= 1
    assert body["capacity"]["docs"] == 1
    assert body["capacity"]["bytes"] > 0


def test_capacity_reports_null_ceilings_when_no_quota_is_configured(client):
    pid = _create(client, "P")["project_id"]

    capacity = client.get(f"/projects/{pid}/documents").json()["capacity"]

    assert capacity["maxBytes"] is None and capacity["maxDocs"] is None, (
        "null means unlimited; a client must say so instead of inventing a denominator"
    )


def test_an_empty_project_reports_an_empty_corpus_not_an_error(client):
    pid = _create(client, "P")["project_id"]

    body = client.get(f"/projects/{pid}/documents").json()

    assert body["documents"] == []
    assert body["capacity"]["docs"] == 0 and body["capacity"]["bytes"] == 0


def test_documents_of_an_unknown_project_is_404(client):
    assert client.get("/projects/project-nope/documents").status_code == 404


def test_an_upload_touches_the_project_so_the_index_sorts_it_as_recent(client):
    created = _create(client, "P")["project"]

    client.post(
        f"/projects/{created['id']}/upload",
        files={"file": ("n.md", io.BytesIO(b"Lamina diez pesos. " * 40), "text/markdown")},
    )

    project = client.get(f"/projects/{created['id']}").json()["project"]
    assert project["updatedAt"] > created["updatedAt"], (
        "feeding a project is activity; it must not sort under ones untouched for weeks"
    )


# --- Gap 4: conversations know their project ----------------------------------


def test_a_conversation_persists_its_project_id(client):
    pid = _create(client, "P")["project_id"]

    client.put("/conversations/conv-uno", json=_conversation("conv-uno", project_id=pid))

    assert client.get("/conversations/conv-uno").json()["projectId"] == pid


def test_recents_filters_the_light_list_to_one_project(client):
    a = _create(client, "A")["project_id"]
    b = _create(client, "B")["project_id"]
    client.put("/conversations/conv-a", json=_conversation("conv-a", project_id=a))
    client.put("/conversations/conv-b", json=_conversation("conv-b", project_id=b))
    client.put("/conversations/conv-loose", json=_conversation("conv-loose"))

    ids = [c["id"] for c in client.get("/conversations", params={"projectId": a}).json()["conversations"]]

    assert ids == ["conv-a"], "Recents must not show another project's chats, nor loose ones"


def test_the_project_id_survives_in_the_summary_list(client):
    pid = _create(client, "P")["project_id"]
    client.put("/conversations/conv-uno", json=_conversation("conv-uno", project_id=pid))

    summary = client.get("/conversations").json()["conversations"][0]

    assert summary["projectId"] == pid, (
        "the field must ride the SUMMARY or Recents costs every full transcript"
    )


def test_a_conversation_outside_any_project_simply_omits_the_field(client):
    client.put("/conversations/conv-loose", json=_conversation("conv-loose"))

    assert "projectId" not in client.get("/conversations/conv-loose").json()


def test_the_unfiltered_list_still_returns_everything(client):
    pid = _create(client, "P")["project_id"]
    client.put("/conversations/conv-a", json=_conversation("conv-a", project_id=pid))
    client.put("/conversations/conv-loose", json=_conversation("conv-loose"))

    ids = sorted(c["id"] for c in client.get("/conversations").json()["conversations"])

    assert ids == ["conv-a", "conv-loose"], "the sidebar must not become project-scoped"


# --- the invariant every new route inherits: another account's id reads as missing


def test_another_account_cannot_read_edit_or_list_a_project_it_does_not_own(client, account):
    pid = _create(client, "de A")["project_id"]

    account("acct-B")

    assert client.get(f"/projects/{pid}").status_code == 404
    assert client.patch(f"/projects/{pid}", json={"name": "secuestrado"}).status_code == 404
    assert client.get(f"/projects/{pid}/documents").status_code == 404, (
        "the knowledge rail is a read of someone's corpus — the same 404, never a 403"
    )


def test_the_patch_a_non_owner_attempted_did_not_land(client, account):
    pid = _create(client, "de A")["project_id"]

    account("acct-B")
    client.patch(f"/projects/{pid}", json={"name": "secuestrado"})
    account("acct-A")

    assert client.get(f"/projects/{pid}").json()["project"]["name"] == "de A"


def test_recents_never_crosses_accounts(client, account):
    pid = _create(client, "de A")["project_id"]
    client.put("/conversations/conv-a", json=_conversation("conv-a", project_id=pid))

    account("acct-B")

    assert client.get("/conversations", params={"projectId": pid}).json()["conversations"] == [], (
        "knowing a project id must not surface another account's chats"
    )
