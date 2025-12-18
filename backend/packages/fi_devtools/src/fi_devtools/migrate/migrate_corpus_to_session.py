from __future__ import annotations

from typing import Sequence

from .._runner import run_legacy_script


def run(args: Sequence[str] | None = None) -> None:
    run_legacy_script("tools/migrate_corpus_to_session_h5.py", list(args or []))
