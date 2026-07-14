"""Projects canary — the /chat/stream route binds the active project's corpus to
the turn so the agent's rag_store tools search THAT corpus.

og118's Projects feature is local-first: the active project id lives in the
browser and is the `corpus_id`. For an uploaded document (a school supply list)
to actually be retrieved when the user asks about it, the turn must tell the
agent which corpus is active. This pins the consumer SEAM: the request's
`corpus_id` reaches `Runner.run_stream(context={"corpus_id": ...})`, where
fi_runner.active_corpus_binding (covered in fi-runner's tests) folds it into the
system prompt. No active project → no binding, byte-identical to before.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import app as app_module
from fastapi.testclient import TestClient


class _SpyRunner:
    """Records the kwargs the route handed run_stream; yields one result event."""

    def __init__(self) -> None:
        self.seen: dict = {}

    async def run_stream(
        self, message, *, session_id=None, request_id=None, history=None, context=None, images=None
    ) -> AsyncIterator[dict]:  # noqa: ANN001
        self.seen = {"message": message, "context": context}
        yield {"type": "result", "result": {"text": "ok"}}


def test_chat_stream_binds_active_corpus(monkeypatch, project_registry) -> None:
    spy = _SpyRunner()
    monkeypatch.setattr(app_module, "_runner", spy)
    client = TestClient(app_module.app)
    # The default (bearer-mode) principal is the legacy account; the corpus must
    # be OWNED by it or the route 404s before binding.
    pid = project_registry.create("legacy-bearer", "P")["id"]

    resp = client.post(
        "/chat/stream",
        json={"message": "¿cuánto cuesta el cuaderno?", "corpus_id": pid},
    )

    assert resp.status_code == 200
    assert spy.seen["context"] == {"corpus_id": pid}


def test_chat_stream_corpus_is_optional(monkeypatch) -> None:
    spy = _SpyRunner()
    monkeypatch.setattr(app_module, "_runner", spy)
    client = TestClient(app_module.app)

    resp = client.post("/chat/stream", json={"message": "hola"})

    assert resp.status_code == 200
    assert (spy.seen["context"] or {}).get("corpus_id") is None


_EXTERNAL_ELEMENT = SimpleNamespace(
    id="element-008-o-oxigeno",
    display_label="8 · O · Oxígeno",
    display_name="Oxígeno",
    symbol="O",
    engine_label="Vultur",
    engine_binding=SimpleNamespace(is_external=True, persona_id="vultur"),
)


class _SpyRag:
    """Fakes RagStoreClient.search; records the query it received."""

    def __init__(self, hits: list[dict] | None = None, error: bool = False) -> None:
        self.hits = hits or []
        self.error = error
        self.seen: dict = {}

    async def search(self, corpus_id, query, *, top_k=5, filters=None):  # noqa: ANN001
        if self.error:
            raise RuntimeError("store down")
        self.seen = {"corpus_id": corpus_id, "query": query, "top_k": top_k}
        return self.hits


def _external_client(monkeypatch, rag: _SpyRag):
    """TestClient wired to an external element + a fake rag store; captures the
    user_text handed to stream_external_turn."""
    spy_runner = _SpyRunner()
    sent: dict = {}

    async def fake_external_turn(*, persona_id, user_text, session_uuid, user_id, history=None):
        sent.update({"persona_id": persona_id, "user_text": user_text})
        yield {"type": "text", "text": "ok"}

    monkeypatch.setattr(
        app_module, "_runner_and_element", lambda token: (spy_runner, _EXTERNAL_ELEMENT)
    )
    monkeypatch.setattr(app_module, "stream_external_turn", fake_external_turn)
    app_module.app.dependency_overrides[app_module.get_rag_store] = lambda: rag
    client = TestClient(app_module.app)
    return client, spy_runner, sent


def test_external_element_gets_server_side_rag_context(monkeypatch, project_registry) -> None:
    """OG118-EXTERNAL-CORPUS-GAP-1 ruta 2: the external engine has no rag_store
    tools, so the route retrieves the project's chunks and folds them into the
    outbound text — the element sees the user's documents."""
    rag = _SpyRag(hits=[{"text": "El cuaderno cuesta 12 pesos.", "similarity": 0.9, "doc_id": "lista"}])
    client, spy_runner, sent = _external_client(monkeypatch, rag)
    pid = project_registry.create("legacy-bearer", "P")["id"]
    try:
        resp = client.post(
            "/chat/stream",
            json={"message": "¿cuánto cuesta el cuaderno?", "element": "oxigeno", "corpus_id": pid},
        )
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_rag_store, None)

    assert resp.status_code == 200
    assert rag.seen["corpus_id"] == pid
    assert rag.seen["query"] == "¿cuánto cuesta el cuaderno?"
    assert "El cuaderno cuesta 12 pesos." in sent["user_text"]  # chunks folded in
    assert "¿cuánto cuesta el cuaderno?" in sent["user_text"]  # original message preserved
    assert spy_runner.seen == {}  # the local runner never ran


def test_external_element_empty_corpus_passes_message_through(monkeypatch, project_registry) -> None:
    rag = _SpyRag(hits=[])
    client, _, sent = _external_client(monkeypatch, rag)
    pid = project_registry.create("legacy-bearer", "P")["id"]
    try:
        resp = client.post(
            "/chat/stream",
            json={"message": "hola", "element": "oxigeno", "corpus_id": pid},
        )
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_rag_store, None)

    assert resp.status_code == 200
    assert sent["user_text"] == "hola"  # no hits → untouched outbound text


def test_external_element_rag_failure_refuses_loud(monkeypatch, project_registry) -> None:
    """A retrieval failure must NOT silently answer without the documents the
    user believes are in play — in-stream error, turn not proxied."""
    rag = _SpyRag(error=True)
    client, spy_runner, sent = _external_client(monkeypatch, rag)
    pid = project_registry.create("legacy-bearer", "P")["id"]
    try:
        resp = client.post(
            "/chat/stream",
            json={"message": "¿cuánto cuesta?", "element": "oxigeno", "corpus_id": pid},
        )
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_rag_store, None)

    assert resp.status_code == 200
    assert '"type": "error"' in resp.text
    assert "No pude consultar los documentos" in resp.text
    assert sent == {}  # the external proxy never ran
    assert spy_runner.seen == {}
