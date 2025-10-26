#!/usr/bin/env python3
"""
Validate Commit Message - Free Intelligence

Enforces Conventional Commits format:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- refactor: Code refactoring
- test: Tests
- chore: Maintenance

Usage (called by pre-commit):
    python3 scripts/validate_commit_message.py <commit-msg-file>
"""

import sys
import re
from pathlib import Path


# Conventional Commits types
VALID_TYPES = {
    'feat',      # New feature
    'fix',       # Bug fix
    'docs',      # Documentation
    'refactor',  # Code refactoring
    'test',      # Tests
    'chore',     # Maintenance
    'perf',      # Performance
    'ci',        # CI/CD
    'build',     # Build system
    'revert',    # Revert commit
}

# Pattern: type(scope): message
COMMIT_PATTERN = re.compile(
    r'^(?P<type>\w+)'                    # Type (required)
    r'(?:\((?P<scope>[\w-]+)\))?'        # Scope (optional)
    r': '                                 # Separator
    r'(?P<message>.+)$'                  # Message (required)
)


def validate_commit_message(message: str) -> tuple[bool, str]:
    """
    Validate commit message format.

    Returns:
        (is_valid, error_message)
    """
    # Skip merge commits
    if message.startswith('Merge'):
        return True, ""

    # Skip revert commits (git revert)
    if message.startswith('Revert'):
        return True, ""

    # Match pattern
    match = COMMIT_PATTERN.match(message)

    if not match:
        return False, (
            "Invalid commit message format!\n\n"
            "Expected: <type>(<scope>): <message>\n"
            "Example: feat(security): add LLM audit policy\n\n"
            f"Valid types: {', '.join(sorted(VALID_TYPES))}"
        )

    commit_type = match.group('type')
    commit_message = match.group('message')

    # Validate type
    if commit_type not in VALID_TYPES:
        return False, (
            f"Invalid commit type: '{commit_type}'\n\n"
            f"Valid types: {', '.join(sorted(VALID_TYPES))}"
        )

    # Validate message not empty
    if not commit_message.strip():
        return False, "Commit message cannot be empty"

    # Validate message doesn't start with uppercase (except proper nouns)
    if commit_message[0].isupper() and not commit_message.startswith(('API', 'HDF5', 'LLM', 'UUID')):
        return False, (
            "Commit message should start with lowercase\n"
            f"Got: '{commit_message}'\n"
            f"Try: '{commit_message[0].lower() + commit_message[1:]}'"
        )

    return True, ""


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_commit_message.py <commit-msg-file>")
        sys.exit(1)

    commit_msg_file = Path(sys.argv[1])

    if not commit_msg_file.exists():
        print(f"Error: File not found: {commit_msg_file}")
        sys.exit(1)

    # Read commit message (first line only)
    message = commit_msg_file.read_text().strip().split('\n')[0]

    # Validate
    is_valid, error = validate_commit_message(message)

    if not is_valid:
        print("\n❌ COMMIT MESSAGE VALIDATION FAILED\n")
        print(error)
        print()
        sys.exit(1)

    print(f"✅ Commit message valid: {message[:60]}...")
    sys.exit(0)


if __name__ == "__main__":
    main()
