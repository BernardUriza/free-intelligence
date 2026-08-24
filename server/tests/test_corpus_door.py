"""The corpus door (backlog #47): the end of the data path the tool did not cover.

The test that matters most is not any single endpoint — it is that a document put
through the DOOR is found by a search run through the TOOL. Those are the two ends
of the path, and verifying only one is what let a user's working upload be reported
as failed.
"""

import json

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from aire import corpus, db
from aire.engine.core import WORKSPACES
from aire.engine.corpus_tool import build_tools, owner_of

TOKEN = "the-owners-own-door-token"
AUTH = {"authorization": f"Bearer {TOKEN}"}
BASE = "og118-doortest"
CHAT = "og118-doortest-chat"
CORPUS = "proj-door"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AIRE_AUTH_TOKEN", TOKEN)
    import aire.bearer
    import aire.door

    monkeypatch.setattr(aire.bearer, "ACCEPTED_TOKENS", (TOKEN,))
    monkeypatch.setattr(aire.door, "ACCEPTED_TOKENS", (TOKEN,))
    from aire.server import app

    for name, md in ((BASE, "persona base"), (CHAT, f"@base {BASE}\n\nalma")):
        home = WORKSPACES / name
        home.mkdir(parents=True, exist_ok=True)
        (home / "CLAUDE.md").write_text(md, encoding="utf-8")
    return TestClient(app, raise_server_exceptions=False)


@pytest_asyncio.fixture()
async def clean():
    yield
    await corpus.drop(BASE, CORPUS)
    await db.close()


def _docs(client) -> dict:
    return client.get(f"/projects/{BASE}/corpus/{CORPUS}/documents", headers=AUTH).json()


def test_the_internet_cannot_read_or_write_a_corpus(client):
    """Everything but /health rides the Bearer. An open corpus door is somebody
    else's documents, readable and overwritable."""
    for call in (lambda: client.get(f"/projects/{BASE}/corpus/{CORPUS}/documents"),
                 lambda: client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents",
                                     json={"doc_id": "x", "text": "y"}),
                 lambda: client.delete(f"/projects/{BASE}/corpus/{CORPUS}")):
        assert call().status_code == 401


def test_a_document_round_trips_through_the_door(client, clean):
    out = client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents", headers=AUTH,
                      json={"doc_id": "acta.md", "text": "El presupuesto fue de 45 mil pesos."}).json()
    assert out == {"doc_id": "acta.md", "chunks": 1, "replaced": True}
    body = _docs(client)
    assert [d["doc_id"] for d in body["documents"]] == ["acta.md"]
    assert body["capacity"]["docs"] == 1 and body["capacity"]["bytes"] > 0


@pytest.mark.asyncio
async def test_what_the_door_writes_is_what_the_tool_finds(client, clean):
    """BOTH ENDS OF THE PATH. The upload lands through the door, in the base
    casita; the search runs through the tool, inside a CHAT casita — and it finds
    it, because both resolve the shelf from `@base` rather than by convention."""
    client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents", headers=AUTH,
                json={"doc_id": "acta.md",
                      "text": "El presupuesto de telemetria fue autorizado por Marisol Vega."})
    tools = {t.name: t.handler for t in build_tools(owner_of(str(WORKSPACES / CHAT)))}
    out = await tools["search_documents"]({"corpus_id": CORPUS, "query": "quién autorizó el presupuesto"})
    hits = json.loads(out["content"][0]["text"])
    assert hits and "Marisol Vega" in hits[0]["text"]


def test_reuploading_replaces_instead_of_duplicating(client, clean):
    for text in ("La reunión es el lunes.", "La reunión es el martes."):
        client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents", headers=AUTH,
                    json={"doc_id": "aviso.md", "text": text})
    assert _docs(client)["capacity"]["chunks"] == 1


def test_deleting_reports_what_it_removed(client, clean):
    client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents", headers=AUTH,
                json={"doc_id": "uno.md", "text": "hola"})
    gone = client.delete(f"/projects/{BASE}/corpus/{CORPUS}/documents/uno.md", headers=AUTH).json()
    assert gone["chunks_removed"] == 1
    missing = client.delete(f"/projects/{BASE}/corpus/{CORPUS}/documents/nada.md", headers=AUTH).json()
    assert missing["chunks_removed"] == 0, "a delete that matched nothing must say so"
    assert _docs(client)["documents"] == []


def test_an_empty_or_nameless_document_is_refused(client, clean):
    for payload in ({"doc_id": "", "text": "algo"}, {"doc_id": "x", "text": "   "}, {}):
        assert client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents",
                           headers=AUTH, json=payload).status_code == 422


def test_a_document_over_the_ceiling_is_refused(client, clean):
    from aire.corpus_door import MAX_DOC_BYTES

    out = client.post(f"/projects/{BASE}/corpus/{CORPUS}/documents", headers=AUTH,
                      json={"doc_id": "enorme.md", "text": "x" * (MAX_DOC_BYTES + 1)})
    assert out.status_code == 413


def test_a_hostile_name_never_reaches_the_store(client):
    assert client.get(f"/projects/..%2F..%2Fetc/corpus/{CORPUS}/documents",
                      headers=AUTH).status_code == 404
    assert client.get(f"/projects/{BASE}/corpus/..%2F..%2Fetc/documents",
                      headers=AUTH).status_code == 404
