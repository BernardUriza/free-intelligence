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

SYSTEM_PROMPT = (
    "You are an agent working inside AIRE, a service that mirrors your session to "
    "the owner's database and streams your work as events. Use your tools whenever "
    "they help. Files you create live in this session's workspace directory."
)

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


def _env(project: str) -> dict[str, str]:
    env = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
    if os.environ.get("AIRE_ISOLATE_CONFIG") == "1":
        # In a container: no Keychain, the credential comes in via env and
        # CLAUDE_CONFIG_DIR keeps the container from storing anything. NOT
        # forced locally (the CLI's credential lives in the macOS Keychain).
        cfg = Path("/tmp/aire-config") / project
        cfg.mkdir(parents=True, exist_ok=True)
        env["CLAUDE_CONFIG_DIR"] = str(cfg)
    return env


def build_options(session_store: Any, project: str, cwd: str,
                  session_uuid: str, mode: str, resuming: bool) -> Any:
    from claude_agent_sdk import ClaudeAgentOptions

    policy = MODES.get(mode, MODES[DEFAULT_MODE])
    kwargs: dict[str, Any] = {
        "system_prompt": SYSTEM_PROMPT,
        "allowed_tools": list(policy["allowed_tools"]),
        "disallowed_tools": list(policy["disallowed_tools"]),
        "permission_mode": policy["permission_mode"],
        "cwd": cwd,
        "setting_sources": [],  # do NOT inherit the machine's CLAUDE.md/settings
        "strict_mcp_config": True,  # do NOT inherit the host machine's MCP servers
        "env": _env(project),
        "session_store": session_store,
        "session_store_flush": "eager",  # no loss window if the process dies
    }
    budget = os.environ.get("AIRE_MAX_BUDGET_USD")
    if budget:
        kwargs["max_budget_usd"] = float(budget)
    # session_id=<uuid> SETS the id of a session being BORN; resume=<uuid>
    # RECOVERS an existing one. Mutually exclusive: passing session_id on a
    # continuation does NOT resume — it starts a new session, clobbering the id
    # and losing the memory. That is why the caller asks the store, not the pool.
    if resuming:
        kwargs["resume"] = session_uuid
    else:
        kwargs["session_id"] = session_uuid
    return ClaudeAgentOptions(**kwargs)
