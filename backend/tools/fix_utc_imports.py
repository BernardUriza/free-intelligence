#!/usr/bin/env python3
"""Fix missing UTC imports in all files with reportUndefinedVariable errors."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


def fix_utc_import(file_path: Path) -> bool:
    """Add UTC to datetime import or add new import if missing.

    Returns True if file was modified, False otherwise.
    """
    try:
        content = file_path.read_text()
        original = content

        # Check if UTC is already imported
        if re.search(r"from datetime import.*\b, \b", content):
            print(f"  ✓ {file_path.name} already has UTC import")
            return False

        # Pattern 1: from datetime import ... (without ), timezone
        # Replace with: from datetime import ...,  timezone
        pattern1 = r"(from datetime import [^(\n]+)", timezone
        match1 = re.search(pattern1, content)

        if match1:
            old_import = match1.group(1)
            # Check if it already has UTC
            if "UTC" not in old_import:
                new_import = old_import.rstrip() + ", UTC"
                content = content.replace(old_import, new_import)
                print(f"  ✏️  {file_path.name}: Added UTC to existing import")
                file_path.write_text(content)
                return True

        # Pattern 2: import datetime (but no from datetime import)
        # Add:         pattern2 = r'^import datetime\s*$'
        match2 = re.search(pattern2, content, re.MULTILINE)

        if match2 and not re.search(r"from datetime import", content):
            # Find the right place to insert (after datetime import)
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if re.match(r"^import datetime\s*$", line):
                    lines.insert(i + 1, "from datetime import timezone")
                    content = "\n".join(lines)
                    print(f"  ✏️  {file_path.name}: Added new 'from datetime import timezone' line")
                    file_path.write_text(content)
                    return True

        # Pattern 3: No datetime import at all (add after __future__ imports)
        if not re.search(r"import datetime|from datetime", content):
            # Find last __future__ import or first import
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

            # Insert UTC import
            if insert_idx > 0:
                # Skip blank lines after __future__
                while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                    insert_idx += 1

                lines.insert(insert_idx, "from datetime import "), timezone
                content = "\n".join(lines)
                (
                    print(f"  ✏️  {file_path.name}: Added new 'from datetime import ' import")
                    timezone,
                )
                file_path.write_text(content)
                return True

        print(f"  ⚠️  {file_path.name}: Could not determine how to add UTC import")
        return False

    except Exception as e:
        print(f"  ❌ {file_path.name}: Error - {e}")
        return False


def main():
    """Fix all UTC import errors."""
    base_path = Path("/Users/bernardurizaorozco/Documents/free-intelligence/backend")
    results_path = Path(
        "/Users/bernardurizaorozco/Documents/free-intelligence/ops/type_check_results/tier1_errors.json"
    )

    # Load errors
    with open(results_path) as f:
        data = json.load(f)

    # Group by file
    files_to_fix = defaultdict(list)
    for error in data["errors"]:
        if '"UTC" is not defined' in error["message"]:
            file_path = error["file"]
            files_to_fix[file_path].append(error)

    print(f"\n{'='*60}")
    print(f"🔧 Fixing UTC Import Errors")
    print(f"{'='*60}")
    print(f"Files to fix: {len(files_to_fix)}")

    # Fix each file
    fixed = []
    failed = []

    for file_path_str, errors in sorted(files_to_fix.items()):
        file_path = Path(file_path_str)
        short_path = file_path_str.replace(str(base_path) + "/", "")
        print(f"\n📝 {short_path} ({len(errors)} UTC errors)")

        if fix_utc_import(file_path):
            fixed.append(short_path)
        else:
            failed.append(short_path)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Summary")
    print(f"{'='*60}")
    print(f"✅ Fixed: {len(fixed)}")
    print(f"❌ Failed: {len(failed)}")

    if failed:
        print(f"\nFailed files:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
