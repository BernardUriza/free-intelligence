"""The MCP half of `fake_codex.py` (#54): what codex-cli 0.164.0 does with the
`-c mcp_servers.<name>.*` overrides, read from its source, done for real.

It parses the overrides as TOML values, spawns the stdio server with the
SCRUBBED environment codex builds (`rmcp-client/src/utils.rs`: a fixed allowlist
plus the names in `env_vars`), speaks MCP to it with the official client, and
denies the call the way `approval_policy="never"` does unless the server is
`default_tools_approval_mode = "approve"` (`core/src/mcp_tool_call.rs`). The
model is the only fake: a prompt `recall: <term>` is the tool call it makes."""

from __future__ import annotations

import os
import tomllib

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_ENV_VARS = ("HOME", "LOGNAME", "PATH", "SHELL", "USER", "LANG", "LC_ALL", "TERM", "TMPDIR", "TZ")
DENIED = "MCP tool call requires approval, but approval policy is never"


def servers(argv: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for flag, value in zip(argv, argv[1:]):
        if flag == "-c" and value.startswith("mcp_servers."):
            dotted, raw = value.split("=", 1)
            _, name, key = dotted.split(".", 2)
            out.setdefault(name, {})[key] = tomllib.loads(f"v = {raw}")["v"]
    return out


def _env(entry: dict) -> dict[str, str]:
    names = (*DEFAULT_ENV_VARS, *entry.get("env_vars", ()))
    return {n: os.environ[n] for n in names if n in os.environ}


async def _call(entry: dict, query: str) -> tuple[str, bool]:
    params = StdioServerParameters(command=entry["command"], args=entry["args"],
                                   env=_env(entry), cwd=entry.get("cwd"))
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("recall", {"query": query, "limit": 5})
    failed = getattr(result, "is_error", None) or getattr(result, "isError", None)  # mcp 2.x / 1.x
    return "\n".join(block.text for block in result.content), bool(failed)


def recall(argv: list[str], query: str) -> tuple[str, bool]:
    """The `memory` server's answer to `recall(query)`, or codex's own refusal."""
    entry = servers(argv).get("memory")
    if entry is None:
        return "unknown MCP server 'memory'", True
    if entry.get("default_tools_approval_mode") != "approve":
        return DENIED, True
    return anyio.run(_call, entry, query)
