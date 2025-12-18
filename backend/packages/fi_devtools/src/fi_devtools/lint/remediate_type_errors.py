from __future__ import annotations

from typing import Sequence

from .._runner import run_legacy_script


def run(args: Sequence[str] | None = None) -> None:
    run_legacy_script("tools/remediate_type_errors.py", list(args or []))
