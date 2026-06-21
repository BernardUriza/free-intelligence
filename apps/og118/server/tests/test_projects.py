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


def _upload(client: TestClient, project_id: str, filename: str, text: str, **kw):
    return client.post(
        f"/projects/{project_id}/upload",
        files={"file": (filename, io.BytesIO(text.encode("utf-8")), "text/markdown")},
        **kw,
    )


def test_upload_ingests_and_is_searchable(client: TestClient, store: RagStoreClient) -> None:
    text = (
        "La papelería vende cuadernos profesionales, lápices y mochilas escolares. "
        "El margen más alto está en las mochilas y los estuches, no en los lápices. "
        "En agosto suben los precios de los cuadernos por el regreso a clases."
    )
    resp = _upload(client, "project-papeleria", "inventario.md", text)
    assert resp.status_code == 200
    body = resp.json()
    assert body["corpus_id"] == "project-papeleria"
    assert body["doc_id"] == "inventario.md"
    assert body["chunks"] > 0
    # The ingested text is retrievable from the SAME corpus the agent searches.
    hits = asyncio.run(store.search("project-papeleria", "¿qué tiene mejor margen?"))
    assert hits and all(h["doc_id"] == "inventario.md" for h in hits)


def test_empty_file_returns_400(client: TestClient) -> None:
    assert _upload(client, "p1", "empty.md", "").status_code == 400


def test_non_utf8_file_returns_400(client: TestClient) -> None:
    resp = client.post(
        "/projects/p1/upload",
        files={"file": ("bin.dat", io.BytesIO(b"\xff\xfe\x00\x01"), "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_bearer_gate_blocks_then_allows(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "_ACCESS_TOKEN", "s3cr3t-token")
    text = "La papelería vende cuadernos profesionales y mochilas escolares de buena calidad."
    assert _upload(client, "p1", "a.md", text).status_code == 401  # no bearer
    ok = _upload(client, "p1", "a.md", text, headers={"Authorization": "Bearer s3cr3t-token"})
    assert ok.status_code == 200
