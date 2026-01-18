from __future__ import annotations

import runpy

import sys
from pathlib import Path


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() and (parent / "backend").exists():
            return parent
    # Fallback to top-most parent
    return current.parents[-1]


def run_legacy_script(relative_path: str, args: list[str] | None = None) -> None:
    """Execute an existing script by relative path from the repo root.

    This keeps legacy tools working while providing modern entry points.
    """

    root = repo_root()
    script_path = root / relative_path
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    sys.argv = [str(script_path), *(args or [])]
    runpy.run_path(str(script_path), run_name="__main__")
