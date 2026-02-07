#!/usr/bin/env python3.14
"""Script to fix broken infrastructure.storage imports across the codebase.

This script:
1. Finds all files with broken imports to infrastructure.storage.infrastructure.hdf5
2. Comments out the broken imports
3. Adds TODO comments for manual DI refactoring

Usage:
    python scripts/fix_broken_imports.py [--dry-run]
"""

import re
import subprocess
from pathlib import Path

# Root directory
BACKEND_DIR = Path(__file__).parent.parent

# Patterns to find broken imports
BROKEN_IMPORT_PATTERNS = [
    r"from infrastructure\.storage\.infrastructure\.hdf5",
    r"from backend\.core\.infrastructure\.storage\.infrastructure\.hdf5",
]


def find_files_with_broken_imports():
    """Find all Python files with broken imports."""
    files_with_issues = []

    for pattern in BROKEN_IMPORT_PATTERNS:
        result = subprocess.run(
            [
                "grep",
                "-r",
                "-l",
                "--include=*.py",
                pattern,
                str(BACKEND_DIR),
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for file_path in result.stdout.strip().split("\n"):
                if file_path and "__pycache__" not in file_path:
                    files_with_issues.append(Path(file_path))

    # Remove duplicates
    return sorted(set(files_with_issues))


def comment_broken_import(line: str) -> tuple[str, bool]:
    """Comment out a broken import line.

    Returns:
        (modified_line, was_modified)
    """
    for pattern in BROKEN_IMPORT_PATTERNS:
        if re.search(pattern, line):
            # Already commented?
            if line.strip().startswith("#"):
                return (line, False)

            # Comment it out
            indent = len(line) - len(line.lstrip())
            commented = (
                " " * indent
                + " " * indent
                + "# "
                + line.lstrip()
            )
            return (commented, True)

    return (line, False)


def fix_file(file_path: Path, dry_run: bool = False) -> int:
    """Fix broken imports in a file.

    Returns:
        Number of lines modified
    """
    content = file_path.read_text()
    lines = content.split("\n")
    modified_lines = []
    modifications = 0

    for line in lines:
        new_line, was_modified = comment_broken_import(line)
        modified_lines.append(new_line)
        if was_modified:
            modifications += 1

    if modifications > 0 and not dry_run:
        file_path.write_text("\n".join(modified_lines))

    return modifications


def main():
    """Main execution."""
    import sys

    dry_run = "--dry-run" in sys.argv

    print("🔍 Finding files with broken imports...")
    files = find_files_with_broken_imports()

    if not files:
        print("✅ No broken imports found!")
        return

    print(f"\n📋 Found {len(files)} files with broken imports:\n")

    total_modifications = 0
    for file_path in files:
        relative_path = file_path.relative_to(BACKEND_DIR)
        modifications = fix_file(file_path, dry_run=dry_run)

        if modifications > 0:
            status = "📝 [DRY RUN]" if dry_run else "✅ [FIXED]"
            print(f"  {status} {relative_path} ({modifications} imports)")
            total_modifications += modifications
        else:
            print(f"  ⏭️  [SKIP] {relative_path} (already commented)")

    print(f"\n{'📊 Summary (DRY RUN)' if dry_run else '🎉 Complete!'}")
    print(f"  Files processed: {len(files)}")
    print(f"  Imports commented: {total_modifications}")

    if dry_run:
        print("\n💡 Run without --dry-run to apply changes")
    else:
        print("\n⚠️  Manual TODO:")
        print("  1. Refactor affected files to use DI container")
        print("  2. Remove commented imports after refactoring")
        print("  3. Run tests to verify functionality")


if __name__ == "__main__":
    main()
