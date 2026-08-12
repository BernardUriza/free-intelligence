"""The gateway door (#30), exercised over REAL sockets: the fake upstream and
the AIRE app each run under their own uvicorn, and every assertion is made from
outside — bytes relayed verbatim and incrementally, headers forwarded
unchanged, errors unwrapped, and the mirror's two rows landing in Postgres."""

import asyncio
import json
import os
import socket
import threading
import time
import uuid
from types import SimpleNamespace

import httpx
import pytest
import uvicorn

import fake_upstream

BODY = {"model": "claude-haiku-4-5", "max_tokens": 16, "stream": True,
        "system": [{"type": "text", "text": "attribution block stays first"}],
        "messages": [{"role": "user", "content": "hi"}]}


def _headers(sid: str) -> dict[str, str]:
    return {"authorization": "Bearer sk-ant-test-not-a-real-key",
            "x-api-key": "sk-test-key",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "context-1m-2025-08-07,output-128k-2025-02-19",
            "x-claude-code-session-id": sid,
            "x-claude-code-agent-id": "agent-1",
            "x-aire-project": "aire-server"}


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _serve(app) -> tuple[str, uvicorn.Server]:
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                           log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("uvicorn did not start")
        time.sleep(0.02)
    return f"http://127.0.0.1:{port}", server


@pytest.fixture(scope="module")
def doors():
    fake_url, fake_server = _serve(fake_upstream.app)
    os.environ["AIRE_GATEWAY_UPSTREAM"] = fake_url
    from aire.server import app as aire_app
    aire_url, aire_server = _serve(aire_app)
    yield SimpleNamespace(aire=aire_url, fake=fake_url)
    fake_server.should_exit = True
    aire_server.should_exit = True


def test_stream_relays_verbatim_and_incrementally(doors):
    sid = str(uuid.uuid4())

    async def go():
        got, first_arrived_early = [], False
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{doors.aire}/v1/messages?beta=true",
                                     json=BODY, headers=_headers(sid)) as r:
                assert r.status_code == 200
                assert "text/event-stream" in r.headers["content-type"]
                async for chunk in r.aiter_raw():
                    if not got:
                        first_arrived_early = fake_upstream.state["finished"] is False
                    got.append(chunk)
        raw = b"".join(got)
        assert raw == b"".join(fake_upstream.STREAM_CHUNKS)
        assert first_arrived_early, "first chunk arrived only after upstream finished (buffered)"
        assert b"event: ping" in raw
        assert b": this comment line must survive the relay" in raw

    asyncio.run(go())


def test_request_headers_and_body_forward_unchanged(doors):
    sid = str(uuid.uuid4())

    async def go():
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{doors.aire}/v1/messages",
                                     json=BODY, headers=_headers(sid)) as r:
                async for _ in r.aiter_raw():
                    pass
        seen = fake_upstream.state["headers"]
        assert seen["authorization"] == "Bearer sk-ant-test-not-a-real-key"
        assert seen["x-api-key"] == "sk-test-key"
        assert seen["anthropic-beta"] == "context-1m-2025-08-07,output-128k-2025-02-19"
        assert seen["anthropic-version"] == "2023-06-01"
        assert seen["x-claude-code-session-id"] == sid
        assert "x-aire-project" not in seen
        assert json.loads(fake_upstream.state["body"])["system"] == BODY["system"]

    asyncio.run(go())


def test_error_body_passes_through_unwrapped(doors):
    async def go():
        headers = {**_headers(str(uuid.uuid4())), "x-fake": "error"}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{doors.aire}/v1/messages", json=BODY, headers=headers)
        assert r.status_code == 400
        assert r.content == fake_upstream.ERROR_BODY

    asyncio.run(go())


def test_count_tokens_and_models_pass_through(doors):
    async def go():
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {**_headers(str(uuid.uuid4())), "x-fake": "error"}
            r = await client.post(f"{doors.aire}/v1/messages/count_tokens",
                                  json=BODY, headers=headers)
            assert (r.status_code, r.content) == (400, fake_upstream.ERROR_BODY)
            assert fake_upstream.state["path"] == "/v1/messages/count_tokens"
            r = await client.get(f"{doors.aire}/v1/models?limit=1000",
                                 headers={"x-fake": "error", "x-api-key": "k"})
            assert r.status_code == 400
            assert fake_upstream.state["path"] == "/v1/models"

    asyncio.run(go())


def test_an_invited_key_is_served_with_aires_own_credential(doors, monkeypatch):
    """#32: the caller carries no Anthropic credential — AIRE lends its own, and
    the upstream must see AIRE's token plus the beta an OAuth token requires,
    never the invite key itself."""
    from aire import lending, tokens
    key = "aire_test_invited_key"
    banked = []
    monkeypatch.setenv("AIRE_LEND_OAUTH_TOKEN", "oat-aires-own")

    async def fake_charge(nickname, usd):  # async, so the real await path is exercised
        banked.append((nickname, usd))

    monkeypatch.setattr(tokens, "charge", fake_charge)
    monkeypatch.setitem(tokens._by_hash, tokens.digest(key),
                        tokens.Holder("test invitee", 1.0, 0.0))

    async def go():
        headers = {"authorization": f"Bearer {key}", "anthropic-version": "2023-06-01",
                   "anthropic-beta": "context-1m-2025-08-07"}
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{doors.aire}/v1/messages",
                                     json=BODY, headers=headers) as r:
                assert r.status_code == 200
                async for _ in r.aiter_raw():
                    pass

    asyncio.run(go())
    seen = fake_upstream.state["headers"]
    assert seen["authorization"] == "Bearer oat-aires-own"
    assert key not in seen["authorization"], "the invite key must never reach Anthropic"
    assert seen["anthropic-beta"] == f"context-1m-2025-08-07,{lending.OAUTH_BETA}"
    assert banked and banked[0][0] == "test invitee"
    assert banked[0][1] > 0, "a real turn that banks $0 is a ceiling that cannot bite"
    assert lending._inflight.get("test invitee") is None, "the slot was returned"


def test_a_spent_invited_key_is_refused_before_upstream(doors, monkeypatch):
    from aire import tokens
    key = "aire_test_spent_key"
    monkeypatch.setenv("AIRE_LEND_OAUTH_TOKEN", "oat-aires-own")
    monkeypatch.setitem(tokens._by_hash, tokens.digest(key),
                        tokens.Holder("broke invitee", 0.05, 0.06))

    async def go():
        async with httpx.AsyncClient(timeout=30) as client:
            return await client.post(f"{doors.aire}/v1/messages", json=BODY,
                                     headers={"authorization": f"Bearer {key}"})

    r = asyncio.run(go())
    assert r.status_code == 402
    assert "spent its budget" in r.json()["error"]["message"]


def test_a_caller_with_their_own_credential_is_still_pass_through(doors, monkeypatch):
    """The lending path must not capture the door: an unrecognised Bearer is a
    stranger's own Anthropic credential and rides upstream untouched."""
    monkeypatch.setenv("AIRE_LEND_OAUTH_TOKEN", "oat-aires-own")

    async def go():
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{doors.aire}/v1/messages", json=BODY,
                                     headers=_headers(str(uuid.uuid4()))) as r:
                async for _ in r.aiter_raw():
                    pass

    asyncio.run(go())
    seen = fake_upstream.state["headers"]
    assert seen["authorization"] == "Bearer sk-ant-test-not-a-real-key"
    assert seen["x-api-key"] == "sk-test-key"
    assert seen["anthropic-beta"] == "context-1m-2025-08-07,output-128k-2025-02-19"


async def _mirror_rows(sid: str, want: int = 2, timeout: float = 8.0):
    import asyncpg
    conn = await asyncpg.connect(os.environ["AIRE_DSN"])
    try:
        deadline = time.monotonic() + timeout
        while True:
            rows = await conn.fetch(
                "SELECT * FROM aire_gateway_log WHERE exchange IN"
                " (SELECT exchange FROM aire_gateway_log WHERE session_id = $1)"
                " ORDER BY seq", sid)
            if len(rows) >= want or time.monotonic() > deadline:
                return rows
            await asyncio.sleep(0.2)
    finally:
        await conn.close()


def _check_request_row(row, sid):
    assert row["session_id"] == sid
    assert row["agent_id"] == "agent-1"
    assert row["project"] == "aire-server"
    assert row["model"] == "claude-haiku-4-5"
    assert json.loads(row["body"])["messages"] == BODY["messages"]


def _check_response_row(row):
    assert row["status"] == 200
    assert row["stop_reason"] == "end_turn"
    assert json.loads(row["usage"]) == {"input_tokens": 10, "output_tokens": 7}
    message = json.loads(row["body"])
    assert message["content"][0] == {"type": "text", "text": "Hello"}
    assert message["model"] == "claude-haiku-4-5"


def test_mirror_appends_both_halves(doors):
    sid = str(uuid.uuid4())

    async def go():
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", f"{doors.aire}/v1/messages",
                                     json=BODY, headers=_headers(sid)) as r:
                async for _ in r.aiter_raw():
                    pass
        rows = await _mirror_rows(sid)
        assert len(rows) == 2, f"expected request+response rows, got {len(rows)}"
        _check_request_row(next(r for r in rows if r["kind"] == "request"), sid)
        _check_response_row(next(r for r in rows if r["kind"] == "response"))

    asyncio.run(go())
