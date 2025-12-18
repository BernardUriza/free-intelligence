#!/usr/bin/env python3
"""Prefix unused variables with underscore to suppress warnings."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path


def run(args: Sequence[str] | None = None) -> None:
    """Fix unused variable warnings by prefixing with underscore."""
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

    warnings = [
        d for d in data.get("generalDiagnostics", []) if d.get("rule") == "reportUnusedVariable"
    ]

    # Group by file and line
    fixes: dict[str, list[tuple[int, str]]] = {}
    for w in warnings:
        filepath = w["file"]
        line_num = w["range"]["start"]["line"] + 1
        try:
            var_name = w["message"].split('"')[1]
        except IndexError:
            continue

        if filepath not in fixes:
            fixes[filepath] = []
        fixes[filepath].append((line_num, var_name))

    # Apply fixes
    fixed_count = 0
    for filepath, changes in fixes.items():
        try:
            with open(filepath) as f:
                lines = f.readlines()

            for line_num, var_name in changes:
                idx = line_num - 1
                if idx < len(lines):
                    original = lines[idx]
                    # Replace variable name with _variable_name
                    # Match whole word only to avoid partial replacements
                    fixed = re.sub(
                        rf"\b{re.escape(var_name)}\b",
                        f"_{var_name}",
                        original,
                        count=1,  # Only first occurrence on the line
                    )
                    if fixed != original:
                        lines[idx] = fixed
                        fixed_count += 1

            with open(filepath, "w") as f:
                f.writelines(lines)

            rel_path = filepath.replace(str(Path.cwd()) + "/", "")
            print(f"\u2713 {rel_path}: fixed {len(changes)} unused variables")
        except Exception as e:
            print(f"\u2717 {filepath}: {e}")

    print(f"\n\u2705 Fixed {fixed_count} unused variables in {len(fixes)} files")


if __name__ == "__main__":
    run()
