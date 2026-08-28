"""The modes dial + the SDK options factory.

complete → no tools, no agentic loop → the substitute for the raw API.
agent    → tools + acceptEdits → the enhancer that executes tools.

NOT bypassPermissions: the CLI REFUSES it outright when the process runs as
root ("cannot be used with root/sudo privileges"), and the daemon does — so
that mode made every agent turn die with exit 1 (verified 2026-07-20 on the
droplet, invisible until the door was finally exercised for real). acceptEdits
auto-approves the file edits an agent needs AND honours `allowed_tools`, which
bypass left decorative. `Bash` stays out; the real filesystem confinement is
`SandboxSettings`, not yet in place — `cwd` is NOT a cage.
"""

import os
from pathlib import Path
from typing import Any

from .cage import cage_hooks
from .contract import TurnSpec

SYSTEM_PROMPT = (
    "You are an agent working inside AIRE, a service that mirrors your session to "
    "the owner's database and streams your work as events. Use your tools whenever "
    "they help. Files you create live in this session's workspace directory."
)


def _casita_prompt(cwd: str) -> str:
    """The casita's fixed prompt, if the `init` endpoint wrote one. Read DIRECTLY
    (not via setting_sources="project", which walks UP the tree and would drag in
    /opt/aire/CLAUDE.md — the server's own). This is the consumer's fixed persona
    living as CONTENT in the casita, so each turn only sends the changing values.

    A file may open with ``@base <project>`` (#36: a per-chat casita is born
    THIN): that line dereferences to the named casita's CLAUDE.md — the shared
    base lives ONCE, every chat inherits its freshest version at spawn, and the
    chat's own file stays pure soul. One level only; a base cannot @base."""
    try:
        text = (Path(cwd) / "CLAUDE.md").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return _debase(text)


def _debase(text: str) -> str:
    from ..names import InvalidName, clean
    from .core import WORKSPACES

    head, _, rest = text.partition("\n")
    if not head.startswith("@base "):
        return text
    try:
        base = (WORKSPACES / clean("project", head[6:].strip()) / "CLAUDE.md").read_text(
            encoding="utf-8").strip()
    except (InvalidName, OSError):
        return text
    return f"{base}\n\n{rest.strip()}" if rest.strip() else base

MODES: dict[str, dict[str, Any]] = {
    "complete": {
        "allowed_tools": [],
        "disallowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"],
        "permission_mode": "default",
    },
    "agent": {
        "allowed_tools": ["Read", "Write", "Glob", "Grep", "WebSearch", "WebFetch"],
        "disallowed_tools": ["Bash"],
        "permission_mode": "acceptEdits",
    },
}
DEFAULT_MODE = "agent"


def _env(project: str, credential_env: dict[str, str] | None = None) -> dict[str, str]:
    # The recursion scrub (#30): the day ANTHROPIC_BASE_URL lands in
    # /etc/aire/env, every spawned CLI would call the daemon back — an infinite
    # loop inside the droplet. The SDK merges this dict ON TOP of os.environ
    # (subprocess_cli.py:431), so a var cannot be removed by omission: the base
    # URL is pinned to the real API (deterministic, no falsy-string semantics
    # to trust) and the gateway token is blanked ("" is falsy to the CLI's
    # env checks — its own log says "…is missing; ignoring").
    env = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
           "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
           "ANTHROPIC_AUTH_TOKEN": ""}
    if os.environ.get("AIRE_ISOLATE_CONFIG") == "1":
        # In a container: no Keychain, the credential comes in via env and
        # CLAUDE_CONFIG_DIR keeps the container from storing anything. NOT
        # forced locally (the CLI's credential lives in the macOS Keychain).
        cfg = Path("/tmp/aire-config") / project
        cfg.mkdir(parents=True, exist_ok=True)
        env["CLAUDE_CONFIG_DIR"] = str(cfg)
    # The active credential slot (#31) rides ON TOP of the scrub — the key sets
    # are disjoint, so the base-URL pin and the injected credential coexist.
    return env | (credential_env or {})


def _mount_tools(kwargs: dict[str, Any], cwd: str, tools: tuple[str, ...]) -> None:
    """Add the vetted registry servers (selected by NAME) to the options —
    in-process only, session-scoped to this casita's project_key. No-op when the
    turn asked for no tools, so the tool-free path is byte-identical to before."""
    if not tools:
        return
    from claude_agent_sdk import project_key_for_directory

    from .tools import resolve
    servers, allowed = resolve(list(tools), project_key_for_directory(cwd), cwd)
    kwargs["mcp_servers"] = servers
    kwargs["allowed_tools"] = list(kwargs["allowed_tools"]) + allowed


def _mount_remote_tools(kwargs: dict[str, Any], remote: tuple[Any, ...]) -> None:
    """Add the caller-hosted HTTP MCP servers (#48) — wired, never executed.

    Each spec already passed the intake's origin allowlist; here it becomes the
    SDK's ``{type: "http"}`` config, so the agent's tool calls travel as
    outbound HTTPS to the caller's own server (where its credentials live —
    the droplet keeps holding none). Allowed whole-server, same as the registry."""
    if not remote:
        return
    servers = kwargs.setdefault("mcp_servers", {})
    allowed = list(kwargs["allowed_tools"])
    for rt in remote:
        config: dict[str, Any] = {"type": "http", "url": rt.url}
        if rt.headers:
            config["headers"] = dict(rt.headers)
        servers[rt.name] = config
        allowed.append(f"mcp__{rt.name}")
    kwargs["allowed_tools"] = allowed


def build_options(session_store: Any, project: str, cwd: str, session_uuid: str,
                  spec: TurnSpec, resuming: bool,
                  credential_env: dict[str, str] | None = None) -> Any:
    from claude_agent_sdk import ClaudeAgentOptions
    policy = MODES.get(spec.mode, MODES[DEFAULT_MODE])
    casita = _casita_prompt(cwd)
    kwargs: dict[str, Any] = {
        "system_prompt": f"{SYSTEM_PROMPT}\n\n{casita}" if casita else SYSTEM_PROMPT,
        "allowed_tools": list(policy["allowed_tools"]),
        "disallowed_tools": list(policy["disallowed_tools"]),
        "permission_mode": policy["permission_mode"],
        "cwd": cwd,
        "setting_sources": [],  # do NOT inherit the machine's CLAUDE.md/settings
        "strict_mcp_config": True,  # do NOT inherit the host machine's MCP servers
        "env": _env(project, credential_env),
        "session_store": session_store,
        "session_store_flush": "eager",  # no loss window if the process dies
        "hooks": cage_hooks(cwd),  # confine file tools to the casita (#24)
    }
    _mount_tools(kwargs, cwd, spec.tools)
    _mount_remote_tools(kwargs, spec.remote_tools)  # after: _mount_tools assigns the dict
    if spec.model:
        kwargs["model"] = spec.model  # → the CLI's `--model`, verbatim (#29 gap 3)
    if budget := os.environ.get("AIRE_MAX_BUDGET_USD"):
        kwargs["max_budget_usd"] = float(budget)
    # session_id=<uuid> SETS the id of a session being BORN; resume=<uuid>
    # RECOVERS an existing one. Mutually exclusive: session_id on a continuation
    # starts a NEW session, clobbering the id and losing the memory — which is
    # why the caller asks the store, not the pool.
    kwargs["resume" if resuming else "session_id"] = session_uuid
    return ClaudeAgentOptions(**kwargs)
