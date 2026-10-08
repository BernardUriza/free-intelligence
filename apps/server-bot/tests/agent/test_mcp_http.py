"""La puerta MCP-sobre-HTTP (`api/mcp_http`) — identidad del servidor, nunca del modelo.

Pinnea el contrato que restaura las 9 tools perdidas de la etapa 2: el agente
del droplet llama de vuelta a este runner por HTTPS, la identidad sale de la
fila durable que `aire_route` publica bajo el lock (`engine/aire_principal`),
y sin token en el env la puerta entera no existe (404, no 401 — un caller sin
credencial no aprende ni que hay superficie)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from persona_runner.api import mcp_http
from persona_runner.engine import aire_principal
from persona_runner.engine.aire_route import memory_tool_specs
from persona_runner.mcp_tools.turn_context import current_principal


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RUNNER_MCP_TOKEN", "tok-1")
    app = FastAPI()
    app.include_router(mcp_http.router)
    return TestClient(app)


def _rpc(client, method, params=None, id_=1, token="tok-1"):  # noqa: S107 — test fixture, not a secret
    return client.post(
        "/mcp/insult-c1",
        headers={"Authorization": f"Bearer {token}"},
        json={"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}},
    )


def test_no_token_env_means_the_door_does_not_exist(monkeypatch):
    monkeypatch.delenv("RUNNER_MCP_TOKEN", raising=False)
    app = FastAPI()
    app.include_router(mcp_http.router)
    c = TestClient(app)
    assert c.post("/mcp/x", json={"jsonrpc": "2.0", "id": 1, "method": "ping"}).status_code == 404


def test_wrong_bearer_is_the_same_404(client):
    r = _rpc(client, "ping", token="wrong")
    assert r.status_code == 404


def test_initialize_and_tools_list_serve_the_ten_tools(client):
    r = _rpc(client, "initialize")
    assert r.json()["result"]["protocolVersion"] == mcp_http.PROTOCOL_VERSION
    tools = _rpc(client, "tools/list").json()["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"get_emotional_arc", "get_disclosure_log", "deep_memory", "search_messages", "get_recent_messages"} <= names
    assert len(tools) == 10
    arc = next(t for t in tools if t["name"] == "get_disclosure_log")
    assert arc["inputSchema"]["type"] == "object"  # the SDK's own converter


def test_a_notification_is_acked_without_a_body(client):
    r = client.post(
        "/mcp/insult-c1",
        headers={"Authorization": "Bearer tok-1"},
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert r.status_code == 202


def test_unknown_method_is_a_jsonrpc_error(client):
    body = _rpc(client, "resources/list").json()
    assert body["error"]["code"] == -32601


def test_call_without_a_live_principal_errors_never_guesses(client, monkeypatch):
    async def no_row(casita):
        return None

    monkeypatch.setattr(aire_principal, "lookup", no_row)
    body = _rpc(client, "tools/call", {"name": "get_emotional_arc", "arguments": {}}).json()
    assert body["result"]["isError"] is True
    assert "no live turn principal" in body["result"]["content"][0]["text"]


def test_call_binds_the_durable_principal_into_the_contextvar(client, monkeypatch):
    async def row(casita):
        assert casita == "insult-c1"  # the path segment this runner chose
        return aire_principal.RemotePrincipal(user_id="u9", channel_id="c9")

    monkeypatch.setattr(aire_principal, "lookup", row)

    seen = {}

    class FakeTool:
        name = "get_emotional_arc"
        description = "d"
        input_schema = {}  # noqa: RUF012 — test double

        @staticmethod
        async def handler(args):
            p = current_principal()
            seen.update(user=p.user_id, channel=p.channel_id, args=args)
            return {"content": [{"type": "text", "text": "arc ok"}]}

    monkeypatch.setitem(mcp_http._TOOLS, "get_emotional_arc", FakeTool)
    body = _rpc(client, "tools/call", {"name": "get_emotional_arc", "arguments": {"days": 7}}).json()
    assert body["result"] == {"content": [{"type": "text", "text": "arc ok"}], "isError": False}
    assert seen == {"user": "u9", "channel": "c9", "args": {"days": 7}}


def test_a_crashing_tool_answers_an_error_not_a_500(client, monkeypatch):
    async def row(casita):
        return aire_principal.RemotePrincipal(user_id="u", channel_id="c")

    monkeypatch.setattr(aire_principal, "lookup", row)

    class Boom:
        name = "deep_memory"
        description = "d"
        input_schema = {}  # noqa: RUF012 — test double

        @staticmethod
        async def handler(args):
            raise RuntimeError("pg died")

    monkeypatch.setitem(mcp_http._TOOLS, "deep_memory", Boom)
    body = _rpc(client, "tools/call", {"name": "deep_memory", "arguments": {}}).json()
    assert body["result"]["isError"] is True
    assert "pg died" not in str(body)  # internals stay server-side


def test_memory_tool_specs_gate_on_both_envs(monkeypatch):
    monkeypatch.delenv("RUNNER_MCP_BASE", raising=False)
    monkeypatch.delenv("RUNNER_MCP_TOKEN", raising=False)
    assert memory_tool_specs("insult-c1") == []
    monkeypatch.setenv("RUNNER_MCP_BASE", "https://r.example.com/")
    assert memory_tool_specs("insult-c1") == []  # token still missing
    monkeypatch.setenv("RUNNER_MCP_TOKEN", "tok-9")
    (spec,) = memory_tool_specs("insult-c1")
    assert spec.url == "https://r.example.com/mcp/insult-c1"
    assert spec.is_http and spec.headers["Authorization"] == "Bearer tok-9"
    assert "tok-9" not in repr(spec)  # the bearer never rides a log line
