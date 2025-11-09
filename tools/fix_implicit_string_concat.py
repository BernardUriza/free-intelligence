#!/usr/bin/env python3
"""Fix implicit string concatenation warnings by adding explicit parentheses."""

import json
import subprocess
from pathlib import Path

# Run pyright and get JSON output
result = subprocess.run(["pyright", "backend/", "--outputjson"], capture_output=True, text=True)

data = json.loads(result.stdout)
warnings = [
    d
    for d in data.get("generalDiagnostics", [])
    if d.get("rule") == "reportImplicitStringConcatenation"
]

# These need manual fixes - add # or fix format
files_to_fix = set()
for w in warnings:
    filepath = Path(w["file"])
    files_to_fix.add(str(filepath))
    line_num = w["range"]["start"]["line"] + 1
    rel_path = str(filepath).replace(str(Path.cwd()) + "/", "")
    print(f"⚠️  {rel_path}:{line_num} - Implicit string concatenation")

print(f"\nℹ️  Found {len(warnings)} implicit string concatenations in {len(files_to_fix)} files")
print("These are typically multi-line regex patterns or long strings.")
print("Recommendation: Add explicit '+' between strings or use parentheses.")
