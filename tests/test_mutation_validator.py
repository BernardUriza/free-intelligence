#!/usr/bin/env python3
"""
Tests for Mutation Validator

FI-DATA-FIX-001
"""

import os
import sys
import tempfile
import unittest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from mutation_validator import (
    MutationViolation,
    get_allowed_patterns,
    is_forbidden_function_name,
    scan_directory,
    scan_file_for_mutations,
    validate_codebase,
)


class TestMutationValidator(unittest.TestCase):
    """Test mutation validator."""

    def test_forbidden_function_names(self) -> None:
        """Test detection of forbidden function names."""
        # Forbidden names
        forbidden = [
            "update_user",
            "delete_interaction",
            "remove_entry",
            "modify_corpus",
            "edit_data",
            "change_value",
            "overwrite_file",
            "truncate_table",
            "drop_database",
            "clear_cache",
            "reset_counter",
            "set_value",
        ]

        for func_name in forbidden:
            is_forbidden, pattern = is_forbidden_function_name(func_name)
            self.assertTrue(is_forbidden, f"Expected '{func_name}' to be forbidden")
            self.assertIsNotNone(pattern)

    def test_allowed_function_names(self) -> None:
        """Test that allowed function names are not flagged."""
        allowed = [
            "append_interaction",
            "add_embedding",
            "get_corpus_stats",
            "read_interactions",
            "fetch_data",
            "find_user",
            "search_corpus",
            "list_sessions",
            "count_interactions",
            "validate_corpus",
            "verify_ownership",
            "check_integrity",
            "init_corpus",
            "generate_id",
            "create_session",
            "build_index",
            "load_config",
            "parse_json",
        ]

        for func_name in allowed:
            is_forbidden, pattern = is_forbidden_function_name(func_name)
            self.assertFalse(
                is_forbidden,
                f"Expected '{func_name}' to be allowed but was flagged with pattern '{pattern}'",
            )

    def test_allowed_exceptions(self) -> None:
        """Test that unittest methods are allowed."""
        exceptions = [
            "setUp",
            "tearDown",
            "setUpClass",
            "tearDownClass",
            "set_logger",
            "set_config",
        ]

        for func_name in exceptions:
            is_forbidden, _ = is_forbidden_function_name(func_name)
            self.assertFalse(is_forbidden)

    def test_scan_file_with_violations(self) -> None:
        """Test scanning file with mutation functions."""
        # Create temp file with violation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def append_data():
    pass

def update_user(user_id):
    '''This should be flagged'''
    pass

def get_data():
    pass
"""
            )
            temp_file = f.name

        try:
            violations = scan_file_for_mutations(temp_file)

            # Should find 1 violation (update_user)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].function_name, "update_user")
            self.assertEqual(violations[0].violation_type, "FORBIDDEN_MUTATION_FUNCTION")
            self.assertIn("append-only", violations[0].message)

        finally:
            os.unlink(temp_file)

    def test_scan_file_without_violations(self) -> None:
        """Test scanning file with only allowed functions."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def append_interaction():
    pass

def get_stats():
    pass

def read_data():
    pass
"""
            )
            temp_file = f.name

        try:
            violations = scan_file_for_mutations(temp_file)
            self.assertEqual(len(violations), 0)

        finally:
            os.unlink(temp_file)

    def test_scan_directory(self) -> None:
        """Test scanning directory for violations."""
        # Create temp directory with multiple files
        temp_dir = tempfile.mkdtemp()

        try:
            # File 1: No violations
            file1 = os.path.join(temp_dir, "good.py")
            with open(file1, "w") as f:
                f.write("def append_data(): pass\n")

            # File 2: Has violation
            file2 = os.path.join(temp_dir, "bad.py")
            with open(file2, "w") as f:
                f.write("def delete_data(): pass\n")

            violations = scan_directory(temp_dir)

            # Should find violations in file2 only
            self.assertEqual(len(violations), 1)
            self.assertIn("bad.py", list(violations.keys())[0])

        finally:
            # Cleanup
            for f in [file1, file2]:
                if os.path.exists(f):
                    os.unlink(f)
            os.rmdir(temp_dir)

    def test_get_allowed_patterns(self) -> None:
        """Test getting allowed patterns."""
        patterns = get_allowed_patterns()

        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)
        self.assertIn("^append_", patterns)
        self.assertIn("^get_", patterns)
        self.assertIn("^read_", patterns)

    def test_validate_codebase_real(self) -> None:
        """Test validation of real backend directory."""
        # This should pass since our codebase has no mutations
        is_valid, violations = validate_codebase("backend", exclude_tests=True)

        # Should be valid (no mutation functions)
        self.assertTrue(is_valid, f"Expected codebase to be valid, found violations: {violations}")
        self.assertEqual(len(violations), 0)

    def test_mutation_violation_dataclass(self) -> None:
        """Test MutationViolation dataclass."""
        violation = MutationViolation(
            file_path="/test/file.py",
            line_number=42,
            function_name="update_user",
            violation_type="FORBIDDEN_MUTATION_FUNCTION",
            message="Test message",
        )

        self.assertEqual(violation.file_path, "/test/file.py")
        self.assertEqual(violation.line_number, 42)
        self.assertEqual(violation.function_name, "update_user")

    def test_scan_file_with_syntax_error(self) -> None:
        """Test that files with syntax errors are handled gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken syntax here!!!")
            temp_file = f.name

        try:
            # Should not raise exception
            violations = scan_file_for_mutations(temp_file)
            # Should return empty (skip invalid files)
            self.assertEqual(len(violations), 0)

        finally:
            os.unlink(temp_file)

    def test_multiple_violations_in_file(self) -> None:
        """Test detection of multiple violations in single file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
def append_data():
    pass

def update_user():
    pass

def delete_session():
    pass

def get_stats():
    pass

def modify_corpus():
    pass
"""
            )
            temp_file = f.name

        try:
            violations = scan_file_for_mutations(temp_file)

            # Should find 3 violations
            self.assertEqual(len(violations), 3)

            violation_names = {v.function_name for v in violations}
            self.assertEqual(violation_names, {"update_user", "delete_session", "modify_corpus"})

        finally:
            os.unlink(temp_file)

    def test_pattern_specificity(self) -> None:
        """Test that patterns are specific (prefix-based)."""
        # These should NOT be flagged (pattern is prefix-based)
        ok_names = [
            "append_update_log",  # starts with append_
            "get_deleted_items",  # starts with get_
            "read_modified_data",  # starts with read_
        ]

        for func_name in ok_names:
            is_forbidden, _ = is_forbidden_function_name(func_name)
            self.assertFalse(
                is_forbidden, f"Expected '{func_name}' to be allowed (pattern is prefix-based)"
            )


if __name__ == "__main__":
    unittest.main()
