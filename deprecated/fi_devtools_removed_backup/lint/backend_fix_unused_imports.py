#!/usr/bin/env python3
"""List unused import errors from pyright for manual review."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from collections.abc import Sequence

from pathlib import Path


def run(args: Sequence[str] | None = None) -> None:
    """List unused imports detected by pyright."""
    target_dir = args[0] if args else "backend/"

    # Run pyright and get JSON output
    result = subprocess.run(
        ["pyright", target_dir, "--outputjson"],
        capture_output=True,
        text=True,
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error: Could not parse pyright output")
        return

    # Filter unused imports
    unused_imports = [
        e for e in data.get("generalDiagnostics", []) if e.get("rule") == "reportUnusedImport"
    ]

    print(f"\n{'=' * 60}")
    print("🔍 Unused Import Errors")
    print(f"{'=' * 60}")
    print(f"Total: {len(unused_imports)}\n")

    # Group by file
    by_file: dict[str, list[dict]] = defaultdict(list)
    for error in unused_imports:
        file_path = error["file"]
        by_file[file_path].append(error)

    for file_path, file_errors in sorted(by_file.items()):
        short_path = file_path.replace(str(Path.cwd()) + "/", "")
        print(f"\n📝 {short_path}")
        for error in file_errors:
            line = error.get("range", {}).get("start", {}).get("line", 0) + 1
            msg = error.get("message", "")
            # Extract import name from message
            import_match = re.search(r'"([^"]+)" is not accessed', msg)
            import_name = import_match.group(1) if import_match else "?"
            print(f"  Line {line}: {import_name}")

    print(f"\n{'=' * 60}")
    print(f"✅ Found {len(unused_imports)} unused imports in {len(by_file)} files")
    print("Recommendation: Remove these imports or prefix with underscore if needed for re-export")


if __name__ == "__main__":
    run()
