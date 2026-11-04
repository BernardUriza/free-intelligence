"""The modes dial — the turn's BUILTIN surface (#37).

Two named notches are the coarse default: `complete` grants no builtin, `agent`
grants the file and web tools under `acceptEdits`. `Bash` is refused in both.

A turn may NARROW its notch with `builtins:[…]`, never widen it: every name must
already be granted by the chosen mode, or the door answers 422 — the same
discipline as an unknown registry tool. What the subset leaves out moves to
`disallowed_tools`, so a narrowed agent cannot reach it at all. `acceptEdits`
rides with `Write`: a subset without it runs under `default`, where a tool
outside `allowed_tools` has no one to approve it. Omitting the field keeps the
notch byte-identical, so every caller that names no builtins sees no change.
"""

from typing import Any

BUILTINS = ("Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch")

MODES: dict[str, dict[str, Any]] = {
    "complete": {
        "allowed_tools": [],
        "disallowed_tools": list(BUILTINS),
        "permission_mode": "default",
    },
    "agent": {
        "allowed_tools": ["Read", "Write", "Glob", "Grep", "WebSearch", "WebFetch"],
        "disallowed_tools": ["Bash"],
        "permission_mode": "acceptEdits",
    },
}
DEFAULT_MODE = "agent"


class BadBuiltins(ValueError):
    """The `builtins` field asked for something the mode does not grant."""


def clean_builtins(raw: Any, mode: str) -> tuple[str, ...] | None:
    """None (absent) keeps the notch whole; a list narrows it, in the notch's order."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(n, str) for n in raw):
        raise BadBuiltins("builtins must be a list of tool names")
    granted = MODES[mode]["allowed_tools"]
    if outside := sorted(set(raw) - set(granted)):
        raise BadBuiltins(f"builtins {outside} are not granted by mode {mode!r}; "
                          f"it grants only {granted} and a turn may only narrow it")
    return tuple(n for n in granted if n in raw)


def policy_for(mode: str, builtins: tuple[str, ...] | None) -> dict[str, Any]:
    """The notch, narrowed to `builtins` when the turn named a subset."""
    notch = MODES.get(mode, MODES[DEFAULT_MODE])
    if builtins is None:
        return notch
    keeps_write = "Write" in builtins
    return {
        "allowed_tools": list(builtins),
        "disallowed_tools": [b for b in BUILTINS
                             if b not in builtins and not (b == "Edit" and keeps_write)],
        "permission_mode": notch["permission_mode"] if keeps_write else "default",
    }
