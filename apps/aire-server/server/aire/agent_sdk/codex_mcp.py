"""The registry tools a Codex turn may mount, as `codex exec -c` overrides (#54).

`codex exec` reaches MCP only through servers it spawns itself, so each vetted
tool becomes a `mcp_servers.<name>` stdio entry whose child is
`aire.engine.stdio_tool` — the same server object the Claude SDK mounts
in-process. Verified against codex-cli 0.164.0's source (`config/src/mcp_types.rs`,
`rmcp-client/src/utils.rs`, `core/src/mcp_tool_call.rs`), three facts shape it:

- the child gets a SCRUBBED environment (HOME, PATH, LANG, … only), so the
  database URL rides as `env_vars`, a list of NAMES codex copies from its own
  environ — the secret never appears in an argv `ps` can read;
- under `approval_policy="never"` a tool that needs approval is DENIED, and the
  default mode needs it for any tool not marked read-only, so the server is
  configured `default_tools_approval_mode="approve"`;
- the child is not sandboxed, so `cwd` is the server root and `-m` finds `aire`.

Only DATABASE-backed tools are offered: the casita-disk tenants would let a
read-only `complete` turn write through a child the sandbox does not cover."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CODEX_TOOLS = frozenset({"memory"})
FORWARDED_ENV = ("AIRE_DATABASE_URL", "AIRE_DB_TIMEOUT", "AIRE_DB_POOL_MAX")
STARTUP_TIMEOUT_S = 30
SERVER_ROOT = str(Path(__file__).resolve().parent.parent.parent)


def split(names: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(what Codex mounts, what it cannot) from the turn's vetted tool names."""
    return (tuple(n for n in names if n in CODEX_TOOLS),
            tuple(n for n in names if n not in CODEX_TOOLS))


def _toml(value: object) -> str:
    """A JSON string or list of strings is valid TOML; `-c` parses it as such."""
    return json.dumps(value)


def server_flags(name: str, project_key: str, cwd: str, session: str = "") -> list[str]:
    """The `-c` pairs that declare one stdio server scoped to this casita."""
    from ..engine.stdio_tool import MODULE
    entry = {"command": sys.executable, "args": ["-m", MODULE, name, project_key, cwd, session],
             "cwd": SERVER_ROOT, "env_vars": list(FORWARDED_ENV),
             "default_tools_approval_mode": "approve"}
    flags = [f"mcp_servers.{name}.{key}={_toml(value)}" for key, value in entry.items()]
    flags.append(f"mcp_servers.{name}.startup_timeout_sec={STARTUP_TIMEOUT_S}")
    # An optional server still starting when the turn's catalog is captured is OMITTED (tool_catalog.rs:376).
    flags.append(f"mcp_servers.{name}.required=true")
    return [part for flag in flags for part in ("-c", flag)]


def flags(names: tuple[str, ...], project_key: str, cwd: str, session: str = "") -> list[str]:
    return [part for name in names for part in server_flags(name, project_key, cwd, session)]
