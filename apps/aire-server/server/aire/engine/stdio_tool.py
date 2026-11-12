"""One vetted registry server, served over stdio to an agent that runs OUTSIDE
the daemon (#54).

The Claude SDK mounts a registry server in-process (`engine/tools.py`). `codex
exec` cannot reach an in-process server: it speaks MCP to a child it spawns, so
the Codex backend configures it with THIS module as that child —
`python -m aire.engine.stdio_tool <name> <project_key> <cwd>`. The server is the
very object the SDK path gets, built by the same factory, so `recall` is one
query with two transports, never two queries.

The registry doctrine holds: the argv is written by the daemon from the turn's
birth, never by the wire. The wire NAMES a tool; the project_key comes from the
casita's directory, so a Codex casita can only recall its own transcript.
"""

from __future__ import annotations

import sys
from typing import Any

import anyio

from .tools import REGISTRY

MODULE = "aire.engine.stdio_tool"


async def serve(name: str, project_key: str, cwd: str) -> None:
    """Speak MCP on stdin/stdout until the agent closes the pipe."""
    from mcp.server.stdio import stdio_server

    server: Any = REGISTRY[name](project_key, cwd)["instance"]
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[0] not in REGISTRY:
        print(f"usage: python -m {MODULE} <{'|'.join(sorted(REGISTRY))}> <project_key> <cwd>",
              file=sys.stderr)
        return 2
    anyio.run(serve, *argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
