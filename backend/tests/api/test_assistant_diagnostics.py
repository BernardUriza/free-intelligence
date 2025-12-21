from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.app.main import create_app

    app = create_app()
    return TestClient(app)


def test_dry_run_redacts_phi(client: TestClient):
    payload = {
        "messages": [
            {"role": "user", "content": "My RFC is ABCDE12345 and my CURP is XAXX010101HDFRRL09"}
        ],
        "model": "gpt-4o-mini",
        "persona": "general_assistant",
    }

    resp = client.post("/api/workflows/aurity/assistant/chat/_dry-run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # user_message should contain hash8 and length
    assert "user_message" in data
    assert "hash8" in data["user_message"]
    assert data["user_message"]["length"] == len(payload["messages"][0]["content"])


def test_public_does_not_call_internal_endpoint(client: TestClient, monkeypatch):
    calls = []

    def fake_post(url, *_args, **_kwargs):
        calls.append(url)

        class R:
            status_code = 200

            def raise_for_status(self):
                return

            def json(self):
                return {}

        return R()

    # Monkeypatch httpx.AsyncClient.post used in internal_llm_client
    import backend.clients.internal_llm_client as clientmod

    monkeypatch.setattr(
        clientmod.httpx.AsyncClient, "post", lambda _self, url, *a, **k: fake_post(url, *a, **k)
    )

    payload = {"messages": [{"role": "user", "content": "Hello"}], "persona": "general_assistant"}
    client.post("/api/workflows/aurity/assistant/chat", json=payload)

    # Ensure none of the recorded URLs start with /internal/llm when called from public
    for c in calls:
        assert not str(c).startswith("/api/internal") and not str(c).startswith("/internal/llm")


def test_trace_propagation_on_dry_run(client: TestClient):
    payload = {
        "messages": [{"role": "user", "content": "Hello trace"}],
        "persona": "general_assistant",
    }
    resp = client.post("/api/workflows/aurity/assistant/chat/_dry-run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    request_id = data["request_id"]

    trace_resp = client.get(f"/api/workflows/aurity/assistant/chat/_trace/{request_id}")
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["request_id"] == request_id
