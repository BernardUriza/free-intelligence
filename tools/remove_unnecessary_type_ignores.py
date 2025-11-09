#!/usr/bin/env python3
"""Remove unnecessary type:ignore comments identified by Pyright."""

import json
import re
import subprocess
from pathlib import Path

# Run pyright and get JSON output
result = subprocess.run(["pyright", "backend/", "--outputjson"], capture_output=True, text=True)

data = json.loads(result.stdout)
warnings = [
    d
    for d in data.get("generalDiagnostics", [])
    if d.get("rule") == "reportUnnecessaryTypeIgnoreComment"
]

# Group by file
files = {}
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
        print(f"✓ {rel_path}: removed {len(line_numbers)} comments")
    except Exception as e:
        print(f"✗ {filepath}: {e}")

print(f"\n✅ Removed {fixed_count} unnecessary type:ignore comments from {len(files)} files")
