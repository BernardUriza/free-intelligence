"""The document door (#55): a project's corpus read back whole, its history, and
who may not read it. The write end is the corpus door, as a consumer writes."""

import uuid

import pytest
from fastapi.testclient import TestClient

from aire import tokens
from aire.engine.core import WORKSPACES

TOKEN = "the-owners-own-door-token"
INVITED = "an-invited-strangers-key"
AUTH = {"authorization": f"Bearer {TOKEN}"}
TEXT = "# Sources — golf\n\n\n## Inserts\n\n| # | Quién |\n|---|---|\n| 1 | Calderón |\n"


@pytest.fixture()
def project():
    name = f"docdoor-{uuid.uuid4().hex[:8]}"
    (WORKSPACES / name).mkdir(parents=True, exist_ok=True)
    return name


@pytest.fixture()
def client(monkeypatch):
    import aire.bearer
    import aire.door

    monkeypatch.setattr(aire.bearer, "ACCEPTED_TOKENS", (TOKEN,))
    monkeypatch.setattr(aire.door, "ACCEPTED_TOKENS", (TOKEN,))
    from aire.server import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        # After startup: the lifespan reloads the invited roster from the database.
        monkeypatch.setitem(tokens._by_hash, tokens.digest(INVITED), tokens.Holder("guest", 5.0, 0.0))
        yield test_client


def _put(client, project, doc_id, text, corpus="exp"):
    return client.post(f"/projects/{project}/corpus/{corpus}/documents", headers=AUTH,
                       json={"doc_id": doc_id, "text": text}).json()


def test_a_slashed_doc_id_round_trips_byte_for_byte(client, project):
    landed = _put(client, project, "casos/golf/sources-golf.md", TEXT)
    assert landed["changed"] and landed["version"] > 0
    got = client.get(f"/projects/{project}/corpus/exp/text/casos/golf/sources-golf.md", headers=AUTH)
    assert got.status_code == 200 and got.json()["text"] == TEXT


def test_history_lists_every_version_and_any_one_reads_back(client, project):
    first = _put(client, project, "backlog.md", "idea uno")
    _put(client, project, "backlog.md", "idea uno\n\nidea dos")
    versions = client.get(f"/projects/{project}/corpus/exp/history/backlog.md", headers=AUTH).json()["versions"]
    assert len(versions) == 2 and versions[-1]["version"] == first["version"]
    old = client.get(f"/projects/{project}/corpus/exp/text/backlog.md",
                     params={"version": first["version"]}, headers=AUTH).json()
    assert old["text"] == "idea uno"


def test_a_slashed_doc_id_can_be_deleted_and_then_reads_404(client, project):
    _put(client, project, "editorial/drafts/golf.md", "borrador")
    gone = client.delete(f"/projects/{project}/corpus/exp/documents/editorial/drafts/golf.md", headers=AUTH)
    assert gone.json()["chunks_removed"] == 1
    assert client.get(f"/projects/{project}/corpus/exp/text/editorial/drafts/golf.md",
                      headers=AUTH).status_code == 404


def test_the_corpora_list_names_each_corpus_with_its_size(client, project):
    _put(client, project, "a.md", "uno", corpus="exp")
    _put(client, project, "b.md", "dos", corpus="editorial")
    corpora = client.get(f"/projects/{project}/corpus", headers=AUTH).json()["corpora"]
    assert [(c["corpus_id"], c["docs"]) for c in corpora] == [("editorial", 1), ("exp", 1)]


def test_an_invited_key_cannot_read_a_projects_documents(client, project):
    _put(client, project, "a.md", "privado")
    guest = {"authorization": f"Bearer {INVITED}"}
    for path in (f"/projects/{project}/corpus", f"/projects/{project}/corpus/exp/text/a.md",
                 f"/projects/{project}/corpus/exp/history/a.md"):
        assert client.get(path, headers=guest).status_code == 403
        assert client.get(path).status_code == 401


def test_a_hostile_project_never_reaches_the_store(client):
    assert client.get("/projects/..%2F..%2Fetc/corpus/exp/text/a.md", headers=AUTH).status_code == 404


def test_an_invited_key_cannot_touch_the_corpus_door_at_all(client, project):
    """Review of #55: the corpus is a project's system of record, so an invited key
    may not write, list, search or delete it either — only the new reads were gated."""
    _put(client, project, "casos/a.md", "privado")
    guest = {"authorization": f"Bearer {INVITED}"}
    base = f"/projects/{project}/corpus/exp"
    for method, path, body in (("POST", f"{base}/documents", {"doc_id": "x.md", "text": "veneno"}),
                               ("GET", f"{base}/documents", None),
                               ("GET", f"{base}/documents/search?q=privado", None),
                               ("DELETE", f"{base}/documents/casos/a.md", None),
                               ("DELETE", base, None)):
        assert client.request(method, path, headers=guest, json=body).status_code == 403, (method, path)
    got = client.get(f"{base}/text/casos/a.md", headers=AUTH)
    assert got.status_code == 200 and got.json()["text"] == "privado"
