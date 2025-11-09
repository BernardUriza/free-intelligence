#!/usr/bin/env python3
"""Fix broken type: ignore comments that were converted to code."""

import re
from pathlib import Path

# Pattern to find broken type ignores: ") [xxx-xxx]" at end of line
pattern = re.compile(r"\)\s+\[[\w\-,\s]+\]\s*$")

fixed_files = 0
total_fixes = 0

for py_file in Path("backend").rglob("*.py"):
    try:
        with open(py_file) as f:
            lines = f.readlines()

        modified = False
        for i, line in enumerate(lines):
            # Look for pattern like: ) [call-arg]
            if pattern.search(line):
                # Extract the type ignore part
                match = re.search(r"\)\s+(\[[\w\-,\s]+\])\s*$", line)
                if match:
                    ignore_part = match.group(1)
                    # Replace with proper comment
                    fixed_line = re.sub(
                        r"\)\s+\[[\w\-,\s]+\]\s*$", f")  # type: ignore{ignore_part}\n", line
                    )
                    if fixed_line != line:
                        lines[i] = fixed_line
                        modified = True
                        total_fixes += 1

        if modified:
            with open(py_file, "w") as f:
                f.writelines(lines)
            print(f"✓ {py_file}")
            fixed_files += 1

    except Exception as e:
        print(f"✗ {py_file}: {e}")

print(f"\n✅ Fixed {total_fixes} broken type:ignore comments in {fixed_files} files")
