from __future__ import annotations

from typing import Sequence

from .._runner import run_legacy_script


def run(args: Sequence[str] | None = None) -> None:
    run_legacy_script("tools/inspect_h5_architecture.py", list(args or []))
