"""The MCP stdio loop both servers share: newline-delimited JSON-RPC, tools only.

Same shape as server-bot's `persona_mcp/server.py` (stdlib, no SDK), so the
servers start under any `python3` with nothing installed. A tool is a
`Tool(name, description, schema, run)`; `run(args) -> Any` returns JSON-able data
or raises, and a raise comes back to the agent as an `isError` result with its
message, never as a dead server.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable

PROTOCOL_VERSION = "2025-06-18"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    schema: dict
    run: Callable[[dict], Any]


def obj(required: Iterable[str] = (), **props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(required)}


def text(payload: Any, failed: bool = False) -> dict:
    body = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=1)
    return {"content": [{"type": "text", "text": body}], "isError": failed}


def call_tool(tools: dict[str, Tool], params: dict) -> dict:
    tool = tools.get(str(params.get("name")))
    if tool is None:
        return text(f"unknown tool {params.get('name')!r}; available: {sorted(tools)}", True)
    try:
        return text(tool.run(dict(params.get("arguments") or {})))
    except Exception as exc:  # noqa: BLE001 - a tool's failure is the agent's to read, not the server's death
        return text(f"{tool.name} failed: {exc}", True)


def handle(server: str, tools: dict[str, Tool], msg: dict) -> dict | None:
    method, id_ = msg.get("method"), msg.get("id")
    if id_ is None:
        return None
    if method == "initialize":
        result: dict = {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
                        "serverInfo": {"name": server, "version": "1.0.0"}}
    elif method == "tools/list":
        result = {"tools": [{"name": t.name, "description": t.description, "inputSchema": t.schema}
                            for t in tools.values()]}
    elif method == "tools/call":
        result = call_tool(tools, dict(msg.get("params") or {}))
    elif method == "ping":
        result = {}
    else:
        return {"jsonrpc": "2.0", "id": id_, "error": {"code": -32601, "message": f"method {method!r} not supported"}}
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def serve(server: str, tools: list[Tool]) -> None:
    table = {t.name: t for t in tools}
    for line in sys.stdin:
        if line.strip():
            reply = handle(server, table, json.loads(line))
            if reply is not None:
                sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                sys.stdout.flush()
