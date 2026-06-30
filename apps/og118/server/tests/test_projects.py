"""proj-upload — POST /projects/{project_id}/upload ingests text into the project's
corpus, the first endpoint that exercises the rag_store tracer end-to-end.

A text file uploaded to a project is chunked + persisted under
``corpus_id=project_id``, then searchable (by the agent's rag_store tools, or
directly). Auth-agnostic for now: behind the same bearer speed-bump as the other
routes; Gate 3 ties the project to a real user. Offline: hdf5 backend + hashing
zero-model embedder (no LLM, no network).
"""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi.testclient import TestClient

import app as app_module
from fi_runner.rag_store import RagStoreClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def store(monkeypatch, tmp_path):
    """Open (no bearer) by default + an isolated tmp HDF5 store per test."""
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", None)
    monkeypatch.setenv("FI_RAG_BACKEND", "hdf5")
    monkeypatch.setenv("FI_RAG_STORE_PATH", str(tmp_path / "proj.h5"))
    rag = RagStoreClient()
    app_module.app.dependency_overrides[app_module.get_rag_store] = lambda: rag
    yield rag
    app_module.app.dependency_overrides.clear()


def _create(client: TestClient, name: str = "P", **kw) -> str:
    """Create a project (owned by the calling principal) and return its id."""
    resp = client.post("/projects", json={"name": name}, **kw)
    assert resp.status_code == 200, resp.text
    return resp.json()["project_id"]


def _upload(client: TestClient, project_id: str, filename: str, text: str, **kw):
    return client.post(
        f"/projects/{project_id}/upload",
        files={"file": (filename, io.BytesIO(text.encode("utf-8")), "text/markdown")},
        **kw,
    )


def test_upload_ingests_and_is_searchable(client: TestClient, store: RagStoreClient) -> None:
    pid = _create(client, "Papelería")
    text = (
        "La papelería vende cuadernos profesionales, lápices y mochilas escolares. "
        "El margen más alto está en las mochilas y los estuches, no en los lápices. "
        "En agosto suben los precios de los cuadernos por el regreso a clases."
    )
    resp = _upload(client, pid, "inventario.md", text)
    assert resp.status_code == 200
    body = resp.json()
    assert body["corpus_id"] == pid
    assert body["doc_id"] == "inventario.md"
    assert body["chunks"] > 0
    # The ingested text is retrievable from the SAME corpus the agent searches.
    hits = asyncio.run(store.search(pid, "¿qué tiene mejor margen?"))
    assert hits and all(h["doc_id"] == "inventario.md" for h in hits)


def test_empty_file_returns_400(client: TestClient) -> None:
    pid = _create(client)
    assert _upload(client, pid, "empty.md", "").status_code == 400


def test_too_short_to_index_returns_422(client: TestClient) -> None:
    # Non-empty text that the chunker drops below its floor (a one-liner) used to
    # return 200 {"chunks": 0} — indexed nothing, searched nothing, no signal. Now
    # it fails LOUD so a short upload can't masquerade as ingested.
    pid = _create(client)
    resp = _upload(client, pid, "nota.md", "Hola mundo")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "TOO_SHORT_TO_INDEX"


def test_non_utf8_file_returns_400(client: TestClient) -> None:
    pid = _create(client)
    resp = client.post(
        f"/projects/{pid}/upload",
        files={"file": ("bin.dat", io.BytesIO(b"\xff\xfe\x00\x01"), "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_bearer_gate_blocks_then_allows(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", "s3cr3t-token")
    hdr = {"Authorization": "Bearer s3cr3t-token"}
    # No bearer → 401 even to create.
    assert client.post("/projects", json={"name": "p"}).status_code == 401
    pid = _create(client, "p", headers=hdr)
    text = (
        "La papelería vende cuadernos profesionales, lápices y mochilas escolares. "
        "El margen más alto está en las mochilas y los estuches, no en los lápices. "
        "En agosto suben los precios de los cuadernos por el regreso a clases."
    )
    assert _upload(client, pid, "a.md", text).status_code == 401  # no bearer
    ok = _upload(client, pid, "a.md", text, headers=hdr)
    assert ok.status_code == 200


# --- proj-account-mint: the corpus_id is minted SERVER-SIDE, never by the client.
# Auth-agnostic first slice of PROJ-ACCOUNT-1 — closes invariant "the client never
# decides corpus_id" (ownership tying to an account is the Gate-3 follow-up).

import re

_PROJECT_ID = re.compile(r"^project-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def test_create_project_mints_server_side_id(client: TestClient) -> None:
    resp = client.post("/projects", json={"name": "Negocio de mamá"})
    assert resp.status_code == 200
    body = resp.json()
    assert _PROJECT_ID.match(body["project_id"]), body["project_id"]
    assert body["name"] == "Negocio de mamá"


def test_create_project_ignores_client_supplied_id(client: TestClient) -> None:
    # The client must NOT be able to choose the corpus_id (would let it land on
    # someone else's corpus). A client-supplied project_id is ignored; the server
    # mints its own.
    resp = client.post("/projects", json={"name": "x", "project_id": "project-victim-corpus"})
    assert resp.status_code == 200
    assert resp.json()["project_id"] != "project-victim-corpus"
    assert _PROJECT_ID.match(resp.json()["project_id"])


def test_create_project_mints_unique_ids(client: TestClient) -> None:
    a = client.post("/projects", json={"name": "a"}).json()["project_id"]
    b = client.post("/projects", json={"name": "b"}).json()["project_id"]
    assert a != b


def test_create_project_bearer_gated(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", "s3cr3t-token")
    assert client.post("/projects", json={"name": "a"}).status_code == 401
    ok = client.post("/projects", json={"name": "a"}, headers={"Authorization": "Bearer s3cr3t-token"})
    assert ok.status_code == 200
