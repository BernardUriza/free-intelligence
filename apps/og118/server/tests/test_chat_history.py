"""og118-continuity canary — the /chat/stream route forwards the client-supplied
conversation history to the Runner.

og118 is local-first: the durable transcript lives in the browser (IndexedDB) and
is replayed on each turn, so continuity survives an ACA replica recycle with NO
server-side store (the prior InMemoryConversationStore was wiped on restart → the
model lost the thread). These tests pin the consumer SEAM: the request's `history`
reaches `Runner.run_stream(history=...)`. The framework-level folding/sanitization
is covered in fi-runner's test_conversation.py.
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
        self.seen = {"message": message, "session_id": session_id, "history": history}
        yield {"type": "result", "result": {"text": "ok"}}


def test_chat_stream_forwards_client_history(monkeypatch) -> None:
    spy = _SpyRunner()
    monkeypatch.setattr(app_module, "_runner", spy)
    client = TestClient(app_module.app)

    body = {
        "message": "han ganado otro!",
        "session_id": "c1",
        "history": [
            {"role": "user", "content": "¿chance de México?"},
            {"role": "assistant", "content": "limitadas"},
        ],
    }
    resp = client.post("/chat/stream", json=body)

    assert resp.status_code == 200
    assert spy.seen["message"] == "han ganado otro!"
    assert spy.seen["session_id"] == "c1"
    assert [(m["role"], m["content"]) for m in spy.seen["history"]] == [
        ("user", "¿chance de México?"),
        ("assistant", "limitadas"),
    ]


def test_chat_stream_history_is_optional(monkeypatch) -> None:
    spy = _SpyRunner()
    monkeypatch.setattr(app_module, "_runner", spy)
    client = TestClient(app_module.app)

    resp = client.post("/chat/stream", json={"message": "hola"})

    assert resp.status_code == 200
    assert spy.seen["history"] is None  # absent → no replay, backend-native path
