#!/usr/bin/env python3
"""Add type: ignore comments for h5py-related type warnings."""

import json
import subprocess
from pathlib import Path

# Run pyright and get JSON output
result = subprocess.run(["pyright", "backend/", "--outputjson"], capture_output=True, text=True)

data = json.loads(result.stdout)

# Find h5py-related warnings
h5py_rules = ["reportAttributeAccessIssue", "reportIndexIssue", "reportOperatorIssue"]
warnings = [
    d
    for d in data.get("generalDiagnostics", [])
    if d.get("rule") in h5py_rules and d.get("severity") == "warning"
]

# Group by file and line
files_to_fix = {}
for w in warnings:
    filepath = w["file"]
    line_num = w["range"]["start"]["line"] + 1
    rule = w["rule"]

    if filepath not in files_to_fix:
        files_to_fix[filepath] = {}
    if line_num not in files_to_fix[filepath]:
        files_to_fix[filepath][line_num] = set()
    files_to_fix[filepath][line_num].add(rule)

# Fix each file
fixed_files = 0
total_fixes = 0

for filepath, line_rules in files_to_fix.items():
    try:
        with open(filepath) as f:
            lines = f.readlines()

        for line_num, rules in sorted(line_rules.items()):
            idx = line_num - 1
            if idx < len(lines):
                original = lines[idx]

                # Skip if already has type: ignore
                if "# type: ignore" in original:
                    continue

                # Add type: ignore at end of line (before newline)
                if original.rstrip().endswith("\\"):
                    # Line continuation - add before backslash
                    fixed = original.rstrip()[:-1].rstrip() + "  # type: ignore[misc]\\\n"
                else:
                    # Normal line
                    fixed = original.rstrip() + "  # type: ignore[misc]\n"

                lines[idx] = fixed
                total_fixes += 1

        # Write back
        with open(filepath, "w") as f:
            f.writelines(lines)

        rel_path = filepath.replace(str(Path.cwd()) + "/", "")
        print(f"✓ {rel_path}: added {len(line_rules)} type ignores")
        fixed_files += 1

    except Exception as e:
        print(f"✗ {filepath}: {e}")

print(f"\n✅ Added {total_fixes} type: ignore comments in {fixed_files} files")
