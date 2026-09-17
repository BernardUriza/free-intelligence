"""The casita cage — a `PreToolUse` hook that confines an agent's file tools to
its own workspace. Backlog #24: `cwd` is NOT a cage, so a plain `Read` reaches
`/etc/aire/env` and a `Write` lands in `/tmp` (both measured 2026-07-20).

Why a hook and NOT `can_use_tool`: the callback only fires when the CLI decides
to ASK for permission, and under `acceptEdits` a `Read` is auto-allowed — the
callback never runs (verified in a live test, it read the secret through it). A
`PreToolUse` hook runs BEFORE every matched tool regardless of the permission
mode, so it is the gate that actually holds.

`.resolve()` collapses `..` and follows symlinks, so a symlink inside the casita
pointing at `/etc` resolves OUTSIDE and is denied. A file tool with no path
argument (a cwd-relative Grep) cannot escape the cwd, so it is allowed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..agent_sdk import HookMatcher

FILE_TOOLS = "Read|Write|Edit|MultiEdit|NotebookEdit|Glob|Grep"
PATH_KEYS = ("file_path", "path", "notebook_path")


def escapes(root: Path, raw: str) -> bool:
    target = Path(raw)
    target = (target if target.is_absolute() else root / target).resolve()
    return target != root and root not in target.parents


def cage_hooks(cwd: str) -> dict[str, Any]:
    """A `hooks=` dict denying any file tool that points outside `cwd`."""
    root = Path(cwd).resolve()

    async def deny_escape(inp: Any, _tool_use_id: Any, _ctx: Any) -> dict[str, Any]:
        ti = inp["tool_input"] if isinstance(inp, dict) else getattr(inp, "tool_input", {})
        raw = next((ti[k] for k in PATH_KEYS if ti.get(k)), None)
        if raw is None or not escapes(root, str(raw)):
            return {}
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": f"denied: {raw} is outside the casita"}}

    return {"PreToolUse": [HookMatcher(matcher=FILE_TOOLS, hooks=[deny_escape])]}
