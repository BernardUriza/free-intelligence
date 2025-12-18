from __future__ import annotations

from typing import Sequence

from .._runner import run_legacy_script


def run(args: Sequence[str] | None = None) -> None:
    run_legacy_script("tools/fix_broken_type_ignores.py", list(args or []))
