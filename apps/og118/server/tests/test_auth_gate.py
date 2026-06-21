"""Account isolation (PROJ-ACCOUNT-1 Gate-3 half): a project is owned by the
account that created it, and no other account can list, read, upload to, or bind
its corpus. Uses the `as_account` fixture (overrides get_principal) to switch
accounts; the autouse `project_registry` keeps it on a tmp store.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

import app as app_module


def _client() -> TestClient:
    return TestClient(app_module.app)


def _upload(client, pid, **kw):
    return client.post(
        f"/projects/{pid}/upload",
        files={"file": ("n.md", io.BytesIO(b"precio secreto del negocio"), "text/markdown")},
        **kw,
    )


def test_projects_are_listed_per_account(as_account) -> None:
    client = _client()
    as_account("acct-A")
    a_pid = client.post("/projects", json={"name": "A1"}).json()["project_id"]
    as_account("acct-B")
    b_pid = client.post("/projects", json={"name": "B1"}).json()["project_id"]

    as_account("acct-A")
    a_list = client.get("/projects").json()["projects"]
    assert [p["id"] for p in a_list] == [a_pid]  # A sees only A's

    as_account("acct-B")
    b_ids = [p["id"] for p in client.get("/projects").json()["projects"]]
    assert b_ids == [b_pid] and a_pid not in b_ids


def test_account_cannot_upload_to_anothers_project(as_account) -> None:
    client = _client()
    as_account("acct-A")
    a_pid = client.post("/projects", json={"name": "A"}).json()["project_id"]
    as_account("acct-B")
    assert _upload(client, a_pid).status_code == 404  # B can't write A's corpus


def test_account_cannot_bind_anothers_corpus(as_account) -> None:
    client = _client()
    as_account("acct-A")
    a_pid = client.post("/projects", json={"name": "A"}).json()["project_id"]
    as_account("acct-B")
    r = client.post("/chat/stream", json={"message": "leak?", "corpus_id": a_pid})
    assert r.status_code == 404  # B can't read A's corpus via chat-bind


def test_account_cannot_delete_anothers_project(as_account) -> None:
    client = _client()
    as_account("acct-A")
    a_pid = client.post("/projects", json={"name": "A"}).json()["project_id"]
    as_account("acct-B")
    assert client.delete(f"/projects/{a_pid}").status_code == 404
    as_account("acct-A")
    assert client.delete(f"/projects/{a_pid}").status_code == 200  # owner can
