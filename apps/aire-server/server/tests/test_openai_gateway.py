"""The OpenAI door (#51), over REAL sockets like the Anthropic one: the fake
upstream plays Azure OpenAI, and every assertion is made from outside — AIRE's
Azure key lent and the caller's AIRE key shed, the usage requested so the turn
can be priced, the exact dollars banked, and every refusal made before a cent
of Azure is spent."""

import asyncio
import json
import os
from types import SimpleNamespace

import httpx
import pytest

import fake_upstream
from test_gateway import _serve
from test_lending import _dict

from aire import openai_gateway

CHAT = {"model": "gpt-4.1", "stream": True, "messages": [{"role": "user", "content": "ping"}]}


@pytest.fixture(scope="module")
def doors():
    fake_url, fake_server = _serve(fake_upstream.app)
    os.environ.setdefault("AIRE_GATEWAY_UPSTREAM", fake_url)
    from aire.server import app as aire_app
    aire_url, aire_server = _serve(aire_app)
    yield SimpleNamespace(aire=aire_url, fake=fake_url)
    fake_server.should_exit = True
    aire_server.should_exit = True


@pytest.fixture
def invited(doors, monkeypatch):
    from aire import lending, tokens
    monkeypatch.setenv("AIRE_OPENAI_UPSTREAM", doors.fake)
    monkeypatch.setenv("AIRE_LEND_AZURE_OPENAI_KEY", "azure-aires-own")
    banked = []

    async def fake_charge(nickname, usd):
        banked.append((nickname, usd))

    monkeypatch.setattr(tokens, "charge", fake_charge)
    lending._inflight.clear()
    fake_upstream.state["path"] = None

    def holder(key, budget=1.0, spent=0.0):
        monkeypatch.setitem(tokens._by_hash, tokens.digest(key),
                            tokens.Holder(f"nick-{key}", budget, spent))
        return f"nick-{key}"

    return SimpleNamespace(banked=banked, holder=holder)


def _post(url, body, headers, stream=False):
    async def go():
        async with httpx.AsyncClient(timeout=30) as client:
            if not stream:
                return await client.post(url, json=body, headers=headers), b""
            async with client.stream("POST", url, json=body, headers=headers) as r:
                return r, b"".join([c async for c in r.aiter_raw()])
    return asyncio.run(go())


def test_a_streamed_chat_is_lent_azure_asked_for_usage_and_banked(doors, invited):
    from aire import lending
    nick = invited.holder("aire_hooks")
    r, raw = _post(f"{doors.aire}/openai/v1/chat/completions", CHAT,
                   {"authorization": "Bearer aire_hooks"}, stream=True)
    assert r.status_code == 200
    assert raw == b"".join(fake_upstream.OPENAI_CHAT_CHUNKS), "relayed byte for byte"
    seen = fake_upstream.state["headers"]
    assert seen["api-key"] == "azure-aires-own"
    assert "authorization" not in seen, "the AIRE key must never reach Azure"
    sent = json.loads(fake_upstream.state["body"])
    assert sent["stream_options"] == {"include_usage": True}
    assert fake_upstream.state["path"] == "/openai/v1/chat/completions"
    # gpt-4.1: 800 fresh input at $2/M + 200 cached at $0.50/M + 100 output at $8/M
    assert invited.banked == [(nick, pytest.approx(0.0025))]
    assert lending._inflight.get(nick) is None, "the slot was returned"


def test_an_azure_style_client_presents_the_key_as_api_key(doors, invited):
    nick = invited.holder("aire_azure_style")
    r, _ = _post(f"{doors.aire}/openai/v1/responses", {"model": "gpt-4.1", "input": "ping"},
                 {"api-key": "aire_azure_style"})
    assert r.status_code == 200
    assert r.json()["usage"]["input_tokens"] == 500
    assert fake_upstream.state["headers"]["api-key"] == "azure-aires-own"
    assert invited.banked == [(nick, pytest.approx(0.0014))]


def test_an_unknown_key_is_refused_in_openai_shape_before_azure(doors, invited):
    r, _ = _post(f"{doors.aire}/openai/v1/chat/completions", CHAT,
                 {"authorization": "Bearer sk-not-an-aire-key"})
    assert r.status_code == 401
    assert r.json()["error"]["type"] == "invalid_request_error"
    assert fake_upstream.state["path"] is None, "Azure was never called"


def test_a_spent_key_is_refused_before_azure(doors, invited):
    invited.holder("aire_broke", budget=0.05, spent=0.06)
    r, _ = _post(f"{doors.aire}/openai/v1/chat/completions", CHAT,
                 {"authorization": "Bearer aire_broke"})
    assert r.status_code == 402
    assert "spent its budget" in r.json()["error"]["message"]
    assert fake_upstream.state["path"] is None


def test_nothing_to_lend_is_a_plain_503_and_frees_the_slot(doors, invited, monkeypatch):
    from aire import lending
    monkeypatch.delenv("AIRE_LEND_AZURE_OPENAI_KEY")
    nick = invited.holder("aire_unlent")
    r, _ = _post(f"{doors.aire}/openai/v1/chat/completions", CHAT,
                 {"authorization": "Bearer aire_unlent"})
    assert r.status_code == 503
    assert lending._inflight.get(nick) is None


def test_an_unbilled_endpoint_does_not_exist_and_frees_the_slot(doors, invited):
    from aire import lending
    nick = invited.holder("aire_embed")
    for _ in range(lending.MAX_INFLIGHT + 1):
        r, _ = _post(f"{doors.aire}/openai/v1/embeddings", {"model": "x", "input": "y"},
                     {"authorization": "Bearer aire_embed"})
        assert r.status_code == 404
    assert lending._inflight.get(nick) is None
    assert fake_upstream.state["path"] is None, "an unpriceable call never reaches Azure"


def test_openai_lending_needs_both_halves_and_sheds_the_callers_key(monkeypatch):
    monkeypatch.delenv("AIRE_OPENAI_UPSTREAM", raising=False)
    monkeypatch.setenv("AIRE_LEND_AZURE_OPENAI_KEY", "k")
    assert openai_gateway.azure_openai() is None
    monkeypatch.setenv("AIRE_OPENAI_UPSTREAM", "https://x.openai.azure.com")
    base, cred = openai_gateway.azure_openai()
    sent = _dict(openai_gateway.lend_openai([("authorization", "Bearer aire_x"), ("api-key", "aire_x"),
                                      ("content-type", "application/json")], cred))
    assert sent == {"content-type": "application/json", "api-key": "k"}
