"""The tool registry — per-turn tools selected by NAME, never by spec.

Backlog #29. The door lets a turn request tools (`{"tools": ["memory"]}`), but
the daemon is internet-open (a revocable canary in lower-trust hands) and runs as
root: it must NEVER accept an arbitrary command to run — that is RCE. So a turn
selects from THIS registry of vetted, in-process servers AIRE ships. The wire can
NAME a server, never DEFINE one; an unknown name is refused, loudly (a typo and an
attack both fail closed).
"""

from __future__ import annotations

from typing import Any

from .memory_tool import build_memory_server
from .persona_tool import build_persona_server

# name -> factory(project_key, cwd) -> an in-process SDK MCP server. In-process
# ONLY: no `command`/`args` ever crosses the wire, so the door cannot be told to
# exec. Each factory closes over its session's scope: the project_key for
# database-backed tools, the casita cwd for disk-backed ones.
REGISTRY: dict[str, Any] = {
    "memory": build_memory_server,
    "persona": build_persona_server,
}


class UnknownTool(Exception):
    """A requested tool name is not in the vetted registry."""


def clean_tools(names: Any) -> list[str]:
    """Validate the door's `tools` field into a deduped list of known registry
    names. Anything else — a dict/spec, a non-string, an unknown name — is refused:
    the wire may only NAME a server, and only one AIRE ships."""
    if not names:
        return []
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise UnknownTool("tools must be a list of registry names (strings)")
    out: list[str] = []
    for n in names:
        if n not in REGISTRY:
            raise UnknownTool(f"unknown tool {n!r}; available: {sorted(REGISTRY)}")
        if n not in out:
            out.append(n)
    return out


def resolve(names: list[str], project_key: str, cwd: str) -> tuple[dict[str, Any], list[str]]:
    """Build the SDK `mcp_servers` mapping and the `allowed_tools` ids for the given
    vetted names. Each server is built session-scoped (closed over this session's
    project_key and casita cwd)."""
    servers: dict[str, Any] = {}
    allowed: list[str] = []
    for name in names:
        servers[name] = REGISTRY[name](project_key, cwd)
        allowed.append(f"mcp__{name}")  # allow the whole server
    return servers, allowed
