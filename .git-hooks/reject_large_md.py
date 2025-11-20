#!/usr/bin/env python3
"""
Pre-commit hook: Reject large markdown files (>150 lines)
Exceptions: README.md, claude.md, files in docs/archive/
"""

import sys
from pathlib import Path

MAX_LINES = 150
EXCEPTIONS = ["README.md", "claude.md"]


def check_file(filepath: Path) -> tuple[bool, int]:
    """Check if file exceeds line limit. Returns (is_too_large, line_count)."""
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = sum(1 for _ in f)
        return lines > MAX_LINES, lines
    except Exception as e:
        print(f"⚠️  Error reading {filepath}: {e}")
        return False, 0


def main():
    """Main entry point."""
    files = [Path(f) for f in sys.argv[1:] if f.endswith(".md")]

    violations = []

    for filepath in files:
        # Skip exceptions
        if filepath.name in EXCEPTIONS:
            continue

        # Skip archived docs
        if "docs/archive" in str(filepath):
            continue

        # Skip node_modules
        if "node_modules" in str(filepath):
            continue

        is_too_large, line_count = check_file(filepath)

        if is_too_large:
            violations.append((filepath, line_count))

    if violations:
        print("❌ COMMIT BLOCKED: Large markdown files detected (>150 lines)")
        print()
        for filepath, line_count in violations:
            print(f"  • {filepath} ({line_count} lines)")
        print()
        print("Policy NO_MD=1 is active. Move large docs to docs/archive/")
        print("and create stubs (≤10 lines) in their original location.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
