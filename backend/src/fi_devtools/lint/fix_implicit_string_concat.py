#!/usr/bin/env python3
"""Fix implicit string concatenation warnings by adding explicit parentheses."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence

from pathlib import Path


def run(args: Sequence[str] | None = None) -> None:
    """Detect implicit string concatenation warnings via pyright."""
    target_dir = args[0] if args else "backend/"

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

    warnings = [
        d
        for d in data.get("generalDiagnostics", [])
        if d.get("rule") == "reportImplicitStringConcatenation"
    ]

    files_to_fix: set[str] = set()
    for w in warnings:
        filepath = Path(w["file"])
        files_to_fix.add(str(filepath))
        line_num = w["range"]["start"]["line"] + 1
        rel_path = str(filepath).replace(str(Path.cwd()) + "/", "")
        print(f"\u26a0\ufe0f  {rel_path}:{line_num} - Implicit string concatenation")

    print(
        f"\n\u2139\ufe0f  Found {len(warnings)} implicit string concatenations in {len(files_to_fix)} files"
    )
    print("These are typically multi-line regex patterns or long strings.")
    print("Recommendation: Add explicit '+' between strings or use parentheses.")


if __name__ == "__main__":
    run()
