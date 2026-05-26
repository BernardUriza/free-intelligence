"""MCP server preflight — verify each MCP server actually starts and exposes
its expected tools BEFORE the first turn runs.

A typical chat-stream API spawns its MCPs lazily (the SDK does so on the first
tool call). That means a broken Bright Data token, a missing ``npx`` binary, or
a fi-core MCP whose Python entrypoint crashes only surfaces when the model
tries the tool — as a generic ``is_error=true`` with no context, mid-roast,
in production.

:func:`probe_mcp` runs a minimal JSON-RPC 2.0 handshake against a stdio MCP
(``initialize`` → ``notifications/initialized`` → ``tools/list``) and returns a
:class:`PreflightResult` with the discovered tools or the failure reason. The
client doesn't need the ``mcp`` Python package — the handshake is small enough
that fi-runner speaks it directly, keeping the preflight module dep-free.

In-process specs (``spec.server`` set) are reported alive with the tools the
spec already declares — they don't go over stdio, so there is nothing to probe.

Typical wiring at API startup::

    @app.on_event("startup")
    async def warm():
        results = await runner.preflight()
        for name, r in results.items():
            if not r.alive:
                log.error("MCP %s dead at boot: %s", name, r.error)

Cheap: each probe spawns the subprocess, exchanges 3 short messages, and tears
it down. Default timeout 10s per server; specs run in parallel.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass

from .backend import MCPServerSpec


@dataclass(frozen=True)
class PreflightResult:
    """The outcome of probing one MCP server.

    ``alive`` is True iff the server started AND responded to ``initialize`` AND
    answered ``tools/list``. ``tools`` is what it actually exposes (so a consumer
    can compare against ``spec.tools`` to catch drift between expected vs actual).
    ``error`` is a short human-readable failure reason when ``alive`` is False;
    None on success."""

    name: str
    alive: bool
    tools: tuple[str, ...] = ()
    error: str | None = None


# Minimal JSON-RPC 2.0 framing for stdio MCP: one JSON object per line, terminated
# with ``\n``. The MCP spec also allows Content-Length framing, but every server
# we use ships line-delimited; keep it simple.
_PROTOCOL_VERSION = "2024-11-05"
_CLIENT_INFO = {"name": "fi-runner-preflight", "version": "1.0"}


async def _send(proc: asyncio.subprocess.Process, payload: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
    await proc.stdin.drain()


async def _recv(proc: asyncio.subprocess.Process, *, timeout: float) -> dict:
    """Read one JSON-RPC response line. Server may print log lines on stderr;
    we only consume stdout so those don't confuse the parser."""
    assert proc.stdout is not None
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
    if not line:
        raise ConnectionError("server closed stdout before responding")
    return json.loads(line.decode("utf-8"))


async def _terminate(proc: asyncio.subprocess.Process) -> None:
    """Best-effort cleanup: SIGTERM, then SIGKILL after 2s. Never raises."""
    if proc.returncode is not None:
        return
    try:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
    except (ProcessLookupError, OSError):
        pass


async def probe_mcp(spec: MCPServerSpec, *, timeout: float = 10.0) -> PreflightResult:
    """Probe one MCP server: spawn → initialize → tools/list → tear down.

    In-process specs (``spec.is_in_process``) are reported alive with the tools
    declared on the spec — there is no subprocess to probe. For stdio specs,
    spawns ``spec.command`` + ``spec.args`` with the env the consumer would use
    in production (``env_passthrough`` honored) and walks the JSON-RPC handshake.

    Failure modes mapped to ``error``:
      - ``"command not found"`` — the executable is missing
      - ``"timeout: <stage>"`` — the server took >``timeout`` seconds at a stage
      - ``"server closed stdout..."`` — the subprocess exited mid-handshake
      - ``"initialize failed: <msg>"`` / ``"tools/list failed: <msg>"`` —
        explicit JSON-RPC error from the server
      - other exception types are reported as ``"<ExcType>: <msg>"``"""
    if spec.is_in_process:
        # In-process server: nothing to spawn. Trust the consumer's declaration.
        return PreflightResult(name=spec.name, alive=True, tools=tuple(spec.tools))
    if not spec.command:
        return PreflightResult(name=spec.name, alive=False, error="spec has no command")

    # env_passthrough=True forwards the FULL os.environ (legacy default for
    # backward-compat); =False uses a safe whitelist that includes only PATH,
    # HOME, USER, LANG, PYTHONPATH, etc. — never secrets. Capabilities default
    # to False to prevent secret leakage to fi-core MCP servers.
    from .backend import safe_subprocess_env
    env = dict(os.environ) if spec.env_passthrough else safe_subprocess_env()
    proc: asyncio.subprocess.Process | None = None
    try:
        try:
            proc = await asyncio.create_subprocess_exec(
                spec.command,
                *spec.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError:
            return PreflightResult(name=spec.name, alive=False, error="command not found")

        # 1. initialize
        await _send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": _CLIENT_INFO,
            },
        })
        try:
            init_resp = await _recv(proc, timeout=timeout)
        except asyncio.TimeoutError:
            return PreflightResult(name=spec.name, alive=False, error="timeout: initialize")
        if "error" in init_resp:
            return PreflightResult(name=spec.name, alive=False, error=f"initialize failed: {init_resp['error']}")

        # 2. initialized notification (no response expected)
        await _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 3. tools/list
        await _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        try:
            list_resp = await _recv(proc, timeout=timeout)
        except asyncio.TimeoutError:
            return PreflightResult(name=spec.name, alive=False, error="timeout: tools/list")
        if "error" in list_resp:
            return PreflightResult(name=spec.name, alive=False, error=f"tools/list failed: {list_resp['error']}")

        raw_tools = (list_resp.get("result") or {}).get("tools") or []
        tools = tuple(t.get("name", "") for t in raw_tools if isinstance(t, dict))
        return PreflightResult(name=spec.name, alive=True, tools=tools)

    except (ConnectionError, json.JSONDecodeError, OSError) as exc:
        return PreflightResult(name=spec.name, alive=False, error=f"{type(exc).__name__}: {exc}")
    finally:
        if proc is not None:
            await _terminate(proc)


async def probe_all(specs: list[MCPServerSpec], *, timeout: float = 10.0) -> dict[str, PreflightResult]:
    """Probe every spec in parallel; return ``{server_name: PreflightResult}``.

    On duplicate names, the LAST result wins — the runner's own ``mcp_servers``
    list de-dupes at compose time anyway, but be defensive at the boundary."""
    if not specs:
        return {}
    results = await asyncio.gather(*(probe_mcp(s, timeout=timeout) for s in specs))
    return {r.name: r for r in results}
