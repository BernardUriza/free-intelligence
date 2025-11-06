#!/usr/bin/env python3
"""Fix unused import errors."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


def get_unused_imports():
    """Extract unused import errors from type check results."""
    results_path = Path(
        "/Users/bernardurizaorozco/Documents/free-intelligence/ops/type_check_results/results.json"
    )

    with open(results_path) as f:
        data = json.load(f)

    # Filter unused imports
    unused_imports = [
        e
        for e in data["details"]
        if e.get("rule") == "reportUnusedImport" and e.get("severity") == "error"
    ]

    return unused_imports


def main():
    """List unused imports for manual review."""
    errors = get_unused_imports()

    print(f"\n{'='*60}")
    print("🔍 Unused Import Errors")
    print(f"{'='*60}")
    print(f"Total: {len(errors)}\n")

    # Group by file
    by_file = defaultdict(list)
    for error in errors:
        file_path = error["file"]
        by_file[file_path].append(error)

    for file_path, file_errors in sorted(by_file.items()):
        short_path = file_path.replace(
            "/Users/bernardurizaorozco/Documents/free-intelligence/backend/", ""
        )
        print(f"\n📝 {short_path}")
        for error in file_errors:
            line = error.get("line", "?")
            msg = error.get("message", "")
            # Extract import name from message
            import_match = re.search(r'"([^"]+)" is not accessed', msg)
            import_name = import_match.group(1) if import_match else "?"
            print(f"  Line {line}: {import_name}")


if __name__ == "__main__":
    main()
