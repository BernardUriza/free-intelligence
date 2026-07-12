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
