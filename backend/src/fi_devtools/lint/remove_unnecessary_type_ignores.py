#!/usr/bin/env python3
"""Remove unnecessary type:ignore comments identified by Pyright."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence

from pathlib import Path


def run(args: Sequence[str] | None = None) -> None:
    """Remove unnecessary type:ignore comments identified by Pyright."""
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
        d
        for d in data.get("generalDiagnostics", [])
        if d.get("rule") == "reportUnnecessaryTypeIgnoreComment"
    ]

    # Group by file
    files: dict[str, list[int]] = {}
    for w in warnings:
        filepath = w["file"]
        line_num = w["range"]["start"]["line"] + 1  # 1-indexed
        if filepath not in files:
            files[filepath] = []
        files[filepath].append(line_num)

    # Process each file
    fixed_count = 0
    for filepath, line_numbers in files.items():
        try:
            with open(filepath) as f:
                lines = f.readlines()

            # Sort in reverse to maintain line numbers
            for line_num in sorted(line_numbers, reverse=True):
                idx = line_num - 1
                if idx < len(lines):
                    original = lines[idx]
                    # Remove type: ignore comments (anywhere in line, preserve rest)
                    fixed = re.sub(r"\s*#\s*type:\s*ignore(\[[\w,\s]+\])?\s*", " ", original)
                    # Clean up any trailing whitespace before newline
                    fixed = (
                        re.sub(r"\s+$", "\n", fixed)
                        if fixed.endswith("\n")
                        else re.sub(r"\s+$", "", fixed) + "\n"
                    )
                    if fixed.strip() != original.strip():
                        lines[idx] = fixed
                        fixed_count += 1

            # Write back
            with open(filepath, "w") as f:
                f.writelines(lines)

            rel_path = filepath.replace(str(Path.cwd()) + "/", "")
            print(f"\u2713 {rel_path}: removed {len(line_numbers)} comments")
        except Exception as e:
            print(f"\u2717 {filepath}: {e}")

    print(
        f"\n\u2705 Removed {fixed_count} unnecessary type:ignore comments from {len(files)} files"
    )


if __name__ == "__main__":
    run()
