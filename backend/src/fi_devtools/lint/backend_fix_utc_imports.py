#!/usr/bin/env python3
"""Fix missing UTC/timezone imports in files with undefined variable errors."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path


def fix_utc_import(file_path: Path) -> bool:
    """Add timezone to datetime import or add new import if missing.

    Returns True if file was modified, False otherwise.
    """
    try:
        content = file_path.read_text()

        # Check if timezone is already imported
        if re.search(r"from datetime import.*timezone", content):
            print(f"  ✓ {file_path.name} already has timezone import")
            return False

        # Pattern 1: from datetime import ... (without timezone)
        pattern1 = r"(from datetime import [^\n]+)"
        match1 = re.search(pattern1, content)

        if match1:
            old_import = match1.group(1)
            if "timezone" not in old_import:
                new_import = old_import.rstrip() + ", timezone"
                content = content.replace(old_import, new_import)
                print(f"  ✏️  {file_path.name}: Added timezone to existing import")
                file_path.write_text(content)
                return True

        # Pattern 2: import datetime (but no from datetime import)
        pattern2 = r"^import datetime\s*$"
        match2 = re.search(pattern2, content, re.MULTILINE)

        if match2 and not re.search(r"from datetime import", content):
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if re.match(r"^import datetime\s*$", line):
                    lines.insert(i + 1, "from datetime import timezone")
                    content = "\n".join(lines)
                    print(f"  ✏️  {file_path.name}: Added new 'from datetime import timezone' line")
                    file_path.write_text(content)
                    return True

        # Pattern 3: No datetime import at all
        if not re.search(r"(import datetime|from datetime import)", content):
            lines = content.split("\n")
            insert_idx = 0

            # Find position after __future__ imports
            for i, line in enumerate(lines):
                if line.startswith("from __future__"):
                    insert_idx = i + 1
                elif line.startswith("import ") or line.startswith("from "):
                    if insert_idx == 0:
                        insert_idx = i
                    break

            if insert_idx > 0:
                # Skip blank lines after __future__
                while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                    insert_idx += 1

                lines.insert(insert_idx, "from datetime import timezone")
                content = "\n".join(lines)
                print(f"  ✏️  {file_path.name}: Added new 'from datetime import timezone' import")
                file_path.write_text(content)
                return True

        print(f"  ⚠️  {file_path.name}: Could not determine how to add timezone import")
        return False

    except Exception as e:
        print(f"  ❌ {file_path.name}: Error - {e}")
        return False


def run(args: Sequence[str] | None = None) -> None:
    """Fix UTC import errors by adding timezone imports."""
    target_dir = args[0] if args else "backend/"

    # Run pyright to find UTC undefined errors
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

    # Find UTC undefined errors
    files_to_fix: dict[str, list[dict]] = defaultdict(list)
    for error in data.get("generalDiagnostics", []):
        if error.get("rule") == "reportUndefinedVariable":
            msg = error.get("message", "")
            if '"UTC" is not defined' in msg or '"timezone" is not defined' in msg:
                files_to_fix[error["file"]].append(error)

    print(f"\n{'=' * 60}")
    print("🔧 Fixing UTC Import Errors")
    print(f"{'=' * 60}")
    print(f"Files to fix: {len(files_to_fix)}")

    # Fix each file
    fixed = []
    failed = []

    for file_path_str, errors in sorted(files_to_fix.items()):
        file_path = Path(file_path_str)
        short_path = file_path_str.replace(str(Path.cwd()) + "/", "")
        print(f"\n📝 {short_path} ({len(errors)} UTC errors)")

        if fix_utc_import(file_path):
            fixed.append(short_path)
        else:
            failed.append(short_path)

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 Summary")
    print(f"{'=' * 60}")
    print(f"✅ Fixed: {len(fixed)}")
    print(f"❌ Failed/Skipped: {len(failed)}")

    if failed:
        print("\nFailed/Skipped files:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    run()
