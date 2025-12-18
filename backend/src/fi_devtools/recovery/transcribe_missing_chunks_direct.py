from __future__ import annotations

from collections.abc import Sequence

from .._runner import run_legacy_script


def run(args: Sequence[str] | None = None) -> None:
    run_legacy_script("tools/transcribe_missing_chunks_direct.py", list(args or []))
