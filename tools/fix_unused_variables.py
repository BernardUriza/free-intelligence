#!/usr/bin/env python3
"""Prefix unused variables with underscore to suppress warnings."""

import json
import re
import subprocess
from pathlib import Path

# Run pyright and get JSON output
result = subprocess.run(["pyright", "backend/", "--outputjson"], capture_output=True, text=True)

data = json.loads(result.stdout)
warnings = [
    d for d in data.get("generalDiagnostics", []) if d.get("rule") == "reportUnusedVariable"
]

# Group by file and line
fixes = {}
for w in warnings:
    filepath = w["file"]
    line_num = w["range"]["start"]["line"] + 1
    var_name = w["message"].split('"')[1]

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
        print(f"✓ {rel_path}: fixed {len(changes)} unused variables")
    except Exception as e:
        print(f"✗ {filepath}: {e}")

print(f"\n✅ Fixed {fixed_count} unused variables in {len(fixes)} files")
