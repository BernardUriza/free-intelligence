#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Mutation Validator

Prevents direct mutation functions in codebase.
Enforces append-only, event-sourced architecture.

FI-DATA-FIX-001
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MutationViolation:
    """Represents a mutation policy violation."""

    file_path: str
    line_number: int
    function_name: str
    violation_type: str
    message: str


# Forbidden function name patterns
FORBIDDEN_PATTERNS = [
    r"^update_",
    r"^delete_",
    r"^remove_",
    r"^modify_",
    r"^edit_",
    r"^change_",
    r"^overwrite_",
    r"^truncate_",
    r"^drop_",
    r"^clear_",
    r"^reset_",
    r"^set_",  # Mutations often use set_*
]

# Allowed exceptions (system/utility functions)
ALLOWED_EXCEPTIONS = [
    "setUp",  # unittest
    "tearDown",  # unittest
    "setUpClass",  # unittest
    "tearDownClass",  # unittest
    "set_logger",  # logger configuration
    "set_config",  # config initialization
]


def is_forbidden_function_name(func_name: str) -> tuple[bool, Optional[str]]:
    """
    Check if function name matches forbidden mutation patterns.

    Args:
        func_name: Function name to check

    Returns:
        (is_forbidden, pattern_matched)

    Examples:
        >>> is_forbidden_function_name("update_interaction")
        (True, '^update_')
        >>> is_forbidden_function_name("append_interaction")
        (False, None)
    """
    # Check allowed exceptions first
    if func_name in ALLOWED_EXCEPTIONS:
        return False, None

    # Check forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if re.match(pattern, func_name):
            return True, pattern

    return False, None


def scan_file_for_mutations(file_path: str) -> list[MutationViolation]:
    """
    Scan Python file for forbidden mutation functions.

    Args:
        file_path: Path to Python file

    Returns:
        List of MutationViolation objects

    Examples:
        >>> violations = scan_file_for_mutations("backend/corpus_ops.py")
        >>> len(violations)
        0
    """
    violations = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content, filename=file_path)

        # Find all function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                is_forbidden, pattern = is_forbidden_function_name(func_name)

                if is_forbidden:
                    violation = MutationViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        function_name=func_name,
                        violation_type="FORBIDDEN_MUTATION_FUNCTION",
                        message=f"Function '{func_name}' matches forbidden pattern '{pattern}'. " +
                        f"Mutations must be event-sourced, not direct. "
                        f"Use append-only operations instead.",
                    )
                    violations.append(violation)

    except SyntaxError:
        # File has syntax errors, skip
        pass
    except Exception:
        # Other errors, skip file
        pass

    return violations


def scan_directory(
    directory: str, exclude_dirs: Optional[list[str]] = None
) -> dict[str, list[MutationViolation]]:
    """
    Scan directory recursively for mutation violations.

    Args:
        directory: Directory to scan
        exclude_dirs: Directories to exclude (e.g., tests, __pycache__)

    Returns:
        Dictionary mapping file paths to violations

    Examples:
        >>> results = scan_directory("backend", exclude_dirs=["__pycache__"])
        >>> total_violations = sum(len(v) for v in results.values())
    """
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".git", "venv", "env", ".venv"]

    results = {}

    directory_path = Path(directory)
    for py_file in directory_path.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in str(py_file) for excluded in exclude_dirs):
            continue

        violations = scan_file_for_mutations(str(py_file))
        if violations:
            results[str(py_file)] = violations

    return results


def get_allowed_patterns() -> list[str]:
    """
    Get list of allowed function name patterns.

    Returns:
        List of allowed patterns
    """
    return [
        "^append_",  # Append operations
        "^add_",  # Add operations (append synonym)
        "^get_",  # Read operations
        "^read_",  # Read operations
        "^fetch_",  # Read operations
        "^find_",  # Query operations
        "^search_",  # Query operations
        "^list_",  # List operations
        "^count_",  # Count operations
        "^validate_",  # Validation
        "^verify_",  # Verification
        "^check_",  # Checks
        "^init_",  # Initialization
        "^generate_",  # Generation
        "^create_",  # Creation (new entities)
        "^build_",  # Building
        "^load_",  # Loading
        "^parse_",  # Parsing
    ]


def validate_codebase(
    backend_dir: str = "backend", exclude_tests: bool = True
) -> tuple[bool, dict[str, list[MutationViolation]]]:
    """
    Validate entire codebase for mutation policy compliance.

    Args:
        backend_dir: Backend directory to validate
        exclude_tests: Whether to exclude test files

    Returns:
        (is_valid, violations_dict)

    Examples:
        >>> is_valid, violations = validate_codebase()
        >>> if not is_valid:
        ...     print(f"Found {sum(len(v) for v in violations.values())} violations")
    """
    exclude_dirs = ["__pycache__", ".git", "venv", "env", ".venv"]
    if exclude_tests:
        exclude_dirs.append("tests")

    violations = scan_directory(backend_dir, exclude_dirs=exclude_dirs)
    is_valid = len(violations) == 0

    return is_valid, violations


def print_violations_report(violations: dict[str, list[MutationViolation]]):
    """
    Print formatted report of violations.

    Args:
        violations: Dictionary of violations by file
    """
    from logger import get_logger

    logger = get_logger()

    if not violations:
        logger.info(
            "MUTATION_SCAN_COMPLETED", message="No mutation functions detected", files_scanned=0
        )
        return

    total_violations = sum(len(v) for v in violations.values())

    logger.warning(
        "MUTATION_VIOLATIONS_DETECTED",
        total_violations=total_violations,
        affected_files=len(violations),
    )

    print("\n🚫 Mutation Policy Violations Detected\n")
    print(f"Total violations: {total_violations}")
    print(f"Affected files: {len(violations)}\n")

    for file_path, file_violations in violations.items():
        print(f"📄 {file_path}:")
        for violation in file_violations:
            print(f"  Line {violation.line_number}: {violation.function_name}")
            print(f"    ❌ {violation.message}\n")

    print("\n💡 Allowed patterns:")
    for pattern in get_allowed_patterns():
        print(f"  ✅ {pattern}")


if __name__ == "__main__":
    """Demo: Mutation validator"""
    import sys

    print("🔍 Mutation Validator - Free Intelligence\n")
    print("Policy: Append-only, event-sourced architecture")
    print("Forbidden: update_, delete_, modify_, remove_, edit_, etc.\n")

    # Validate backend directory
    is_valid, violations = validate_codebase("backend", exclude_tests=True)

    if is_valid:
        print("✅ VALIDATION PASSED")
        print("   No mutation functions detected in backend/")
        print("   Codebase complies with append-only policy\n")
    else:
        print_violations_report(violations)
        sys.exit(1)

    # Show allowed patterns
    print("\n✅ Allowed function patterns:")
    for pattern in get_allowed_patterns():
        print(f"  • {pattern}")
