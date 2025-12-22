#!/usr/bin/env python3
"""Migrate task_repository.py from CORPUS_PATH to locked_session_h5().

This script performs surgical replacement of all h5py.File(CORPUS_PATH)
instances with locked_session_h5(session_id, mode=X).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from pathlib import Path


def run(args: Sequence[str] | None = None) -> None:
    """Migrate h5py.File(CORPUS_PATH) to locked_session_h5()."""
    target_file = (
        args[0] if args else "backend/src/fi_storage/infrastructure/hdf5/task_repository.py"
    )
    target_path = Path(target_file)

    if not target_path.exists():
        print(f"❌ Target file not found: {target_path}")
        return

    content = target_path.read_text()
    original = content

    # Replace pattern: with h5py.File(CORPUS_PATH, "r") as f:
    pattern_r = r'with h5py\.File\(CORPUS_PATH, "r"\) as f:'
    replacement_r = 'with locked_session_h5(session_id, mode="r") as f:'
    content = re.sub(pattern_r, replacement_r, content)

    # Replace pattern: with h5py.File(CORPUS_PATH, "a") as f:
    pattern_a = r'with h5py\.File\(CORPUS_PATH, "a"\) as f:'
    replacement_a = 'with locked_session_h5(session_id, mode="a") as f:'
    content = re.sub(pattern_a, replacement_a, content)

    count_r = len(re.findall(replacement_r, content))
    count_a = len(re.findall(replacement_a, content))

    print(f"Migrated {count_r} read operations")
    print(f"Migrated {count_a} write operations")
    print(f"Total: {count_r + count_a} migrations")

    if content != original:
        target_path.write_text(content)
        print("✅ Migration complete")
    else:
        print("ℹ️  No changes needed (already migrated or no matches)")


if __name__ == "__main__":
    run()
