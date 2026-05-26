"""Tests for the MCP preflight: probe_mcp + probe_all + Runner.preflight.

Strategy: spawn a tiny stdio MCP server written inline as a python -c script.
It speaks just enough JSON-RPC 2.0 to answer initialize + tools/list, so the
probe has a real subprocess to talk to without pulling any external server.
The fakes are kept short (~10 lines) so the wire contract is auditable inline.
"""

from __future__ import annotations

import sys

import pytest

from fi_runner import MCPServerSpec, PreflightResult, probe_all, probe_mcp

# --- Inline fake servers (python -c bodies) --------------------------------
#
# Each fake reads one JSON line per request from stdin and writes one JSON line
# per response to stdout. They DON'T validate the request fully — just enough
# to pretend to be MCP-compliant for the probe handshake. Single-line ``\n`` is
# what probe_mcp speaks; matches the line-delimited mode every server we use.

_FAKE_OK = (
    "import json,sys\n"
    "# initialize\n"
    "req=json.loads(sys.stdin.readline());"
    "sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':req['id'],"
    "'result':{'protocolVersion':'2024-11-05','capabilities':{},"
    "'serverInfo':{'name':'fake','version':'1.0'}}})+'\\n');"
    "sys.stdout.flush()\n"
    "# notifications/initialized (no response)\n"
    "sys.stdin.readline()\n"
    "# tools/list\n"
    "req=json.loads(sys.stdin.readline());"
    "sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':req['id'],"
    "'result':{'tools':[{'name':'echo'},{'name':'add'}]}})+'\\n');"
    "sys.stdout.flush()\n"
)

_FAKE_HANGS = "import time; time.sleep(60)\n"

_FAKE_INIT_ERROR = (
    "import json,sys\n"
    "req=json.loads(sys.stdin.readline());"
    "sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':req['id'],"
    "'error':{'code':-32600,'message':'bad init'}})+'\\n');"
    "sys.stdout.flush()\n"
)


def _spec(body: str, name: str = "fake") -> MCPServerSpec:
    return MCPServerSpec(name=name, command=sys.executable, args=["-c", body])


# --- probe_mcp -------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_discovers_tools_on_well_behaved_server():
    result = await probe_mcp(_spec(_FAKE_OK))
    assert result.alive is True
    assert result.tools == ("echo", "add")
    assert result.error is None
    assert result.name == "fake"


@pytest.mark.asyncio
async def test_probe_reports_missing_command():
    spec = MCPServerSpec(name="ghost", command="/__nope/__not_a_real_binary__")
    result = await probe_mcp(spec)
    assert result.alive is False
    assert result.error == "command not found"


@pytest.mark.asyncio
async def test_probe_reports_timeout_when_server_hangs():
    # 0.5s timeout — the fake sleeps 60s, so we hit timeout: initialize.
    result = await probe_mcp(_spec(_FAKE_HANGS), timeout=0.5)
    assert result.alive is False
    assert result.error == "timeout: initialize"


@pytest.mark.asyncio
async def test_probe_surfaces_jsonrpc_error_on_initialize():
    result = await probe_mcp(_spec(_FAKE_INIT_ERROR))
    assert result.alive is False
    assert result.error is not None
    assert result.error.startswith("initialize failed:")
    assert "bad init" in result.error


@pytest.mark.asyncio
async def test_probe_in_process_spec_is_alive_with_declared_tools():
    # No subprocess to spawn; trust the consumer's declaration.
    sentinel = object()
    spec = MCPServerSpec(name="in_proc", server=sentinel, tools=("a", "b"))
    result = await probe_mcp(spec)
    assert result == PreflightResult(name="in_proc", alive=True, tools=("a", "b"), error=None)


@pytest.mark.asyncio
async def test_probe_spec_without_command_is_dead():
    # Defensive: a spec with neither stdio command NOR in-process server.
    spec = MCPServerSpec(name="empty")
    result = await probe_mcp(spec)
    assert result.alive is False
    assert result.error == "spec has no command"


# --- probe_all -------------------------------------------------------------


@pytest.mark.asyncio
async def test_probe_all_runs_in_parallel_and_keys_by_name():
    specs = [_spec(_FAKE_OK, "a"), _spec(_FAKE_OK, "b")]
    out = await probe_all(specs, timeout=5.0)
    assert set(out) == {"a", "b"}
    assert all(r.alive for r in out.values())


@pytest.mark.asyncio
async def test_probe_all_empty_returns_empty_dict():
    assert await probe_all([]) == {}


# --- Runner.preflight ------------------------------------------------------


@pytest.mark.asyncio
async def test_runner_preflight_probes_extra_mcp_servers():
    # No real backend needed — preflight resolves capabilities/extra_mcp_servers
    # and doesn't run a turn. Use a dummy stand-in for the backend field.
    from fi_runner import Runner

    class _DummyBackend:
        async def run_turn(self, **_kw):  # pragma: no cover
            raise NotImplementedError

    runner = Runner(
        backend=_DummyBackend(),  # type: ignore[arg-type]
        persona="t",
        extra_mcp_servers=[_spec(_FAKE_OK, "brightdata")],
    )
    out = await runner.preflight(timeout=5.0)
    assert "brightdata" in out
    assert out["brightdata"].alive is True
    assert out["brightdata"].tools == ("echo", "add")
