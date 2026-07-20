"""The casita cage — a `can_use_tool` gate that confines an agent's file tools
to its own workspace. Backlog #24: `cwd` is NOT a cage on its own, so a plain
`Read` reaches `/etc/aire/env` and a `Write` lands in `/tmp`. This is the SDK's
sanctioned mechanism for it (SandboxSettings confines only bash; its docstring
sends filesystem reads to a permission gate — this IS that gate).

`.resolve()` collapses `..` and follows symlinks, so a symlink planted inside the
casita that points at `/etc` resolves OUTSIDE and is denied. A file tool with no
path argument (a cwd-relative Grep) is allowed: it cannot escape the cwd.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

FILE_TOOLS = {"Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "Glob", "Grep"}
PATH_KEYS = ("file_path", "path", "notebook_path")


def _escapes(root: Path, raw: str) -> bool:
    target = Path(raw)
    target = (target if target.is_absolute() else root / target).resolve()
    return target != root and root not in target.parents


def make_cage(cwd: str) -> Any:
    """A `can_use_tool` callback denying any file tool that points outside `cwd`."""
    root = Path(cwd).resolve()

    async def gate(tool: str, tool_input: dict[str, Any], _ctx: Any) -> Any:
        if tool not in FILE_TOOLS:
            return PermissionResultAllow()
        raw = next((tool_input[k] for k in PATH_KEYS if tool_input.get(k)), None)
        if raw is None or not _escapes(root, str(raw)):
            return PermissionResultAllow()
        return PermissionResultDeny(message=f"denied: {raw} is outside the casita")

    return gate
