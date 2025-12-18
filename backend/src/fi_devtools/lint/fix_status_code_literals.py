#!/usr/bin/env python3
"""Fix status code literals to use StatusCode enum."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path


def run(args: Sequence[str] | None = None) -> None:
    """Fix status code literals to use StatusCode enum."""
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
        if d.get("rule") == "reportArgumentType"
        and "Literal['success']" in d.get("message", "")
        and "StatusCode" in d.get("message", "")
    ]

    # Group by file
    files_to_fix: dict[str, set[int]] = {}
    for w in warnings:
        filepath = w["file"]
        if filepath not in files_to_fix:
            files_to_fix[filepath] = set()
        files_to_fix[filepath].add(w["range"]["start"]["line"] + 1)

    # Fix each file
    fixed_files = 0
    total_fixes = 0

    for filepath, line_numbers in files_to_fix.items():
        try:
            with open(filepath) as f:
                lines = f.readlines()

            # Check if StatusCode is already imported
            has_import = any(
                "from backend.schemas" in line and "StatusCode" in line for line in lines
            )
            needs_import = False

            # Fix lines
            for line_num in sorted(line_numbers):
                idx = line_num - 1
                if idx < len(lines):
                    original = lines[idx]
                    # Replace status="success" with status=StatusCode.SUCCESS
                    fixed = re.sub(
                        r'status\s*=\s*["\']success["\']', "status=StatusCode.SUCCESS", original
                    )
                    if fixed != original:
                        lines[idx] = fixed
                        total_fixes += 1
                        if not has_import:
                            needs_import = True

            # Add import if needed
            if needs_import:
                # Find the right place to add import (after other backend.schemas imports)
                insert_idx = 0
                for i, line in enumerate(lines):
                    if "from backend.schemas" in line:
                        # Add StatusCode to existing import
                        if "import" in line and "StatusCode" not in line:
                            lines[i] = (
                                line.rstrip().rstrip(")") + ", StatusCode)\n"
                                if line.rstrip().endswith(")")
                                else line.rstrip() + ", StatusCode\n"
                            )
                            needs_import = False
                            break
                    elif line.startswith("from ") or line.startswith("import "):
                        insert_idx = i + 1

                if needs_import:
                    lines.insert(insert_idx, "from backend.schemas import StatusCode\n")

            # Write back
            with open(filepath, "w") as f:
                f.writelines(lines)

            rel_path = filepath.replace(str(Path.cwd()) + "/", "")
            print(f"\u2713 {rel_path}: fixed {len(line_numbers)} status literals")
            fixed_files += 1

        except Exception as e:
            print(f"\u2717 {filepath}: {e}")

    print(f"\n\u2705 Fixed {total_fixes} status literals in {fixed_files} files")


if __name__ == "__main__":
    run()
