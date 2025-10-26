"""
Tests para Commit Message Validator

Cobertura:
- Conventional Commits format validation
- Valid types (feat, fix, docs, etc.)
- Message format (lowercase, not empty)
- Scope validation (optional)

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Task: FI-CICD-FEAT-001
"""

import unittest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_commit_message import validate_commit_message, VALID_TYPES


class TestCommitMessageValidator(unittest.TestCase):
    """Tests para validación de mensajes de commit."""

    def test_valid_feat_with_scope(self):
        """Debe aceptar feat con scope."""
        message = "feat(security): add LLM audit policy"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_valid_fix_without_scope(self):
        """Debe aceptar fix sin scope."""
        message = "fix: resolve mutation validator bug"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_valid_docs(self):
        """Debe aceptar docs."""
        message = "docs: update README with installation steps"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_valid_refactor(self):
        """Debe aceptar refactor."""
        message = "refactor(core): simplify event validator logic"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_valid_test(self):
        """Debe aceptar test."""
        message = "test: add tests for export policy"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_valid_chore(self):
        """Debe aceptar chore."""
        message = "chore: update dependencies"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_invalid_type(self):
        """Debe rechazar tipo inválido."""
        message = "invalid: this is wrong"
        is_valid, error = validate_commit_message(message)
        self.assertFalse(is_valid)
        self.assertIn("Invalid commit type", error)

    def test_invalid_no_colon(self):
        """Debe rechazar mensaje sin colon."""
        message = "feat add feature"
        is_valid, error = validate_commit_message(message)
        self.assertFalse(is_valid)
        self.assertIn("Invalid commit message format", error)

    def test_invalid_no_space_after_colon(self):
        """Debe rechazar mensaje sin espacio después de colon."""
        message = "feat:add feature"
        is_valid, error = validate_commit_message(message)
        self.assertFalse(is_valid)

    def test_invalid_uppercase_message(self):
        """Debe rechazar mensaje que empieza con mayúscula."""
        message = "feat: Add new feature"
        is_valid, error = validate_commit_message(message)
        self.assertFalse(is_valid)
        self.assertIn("lowercase", error)

    def test_valid_uppercase_proper_noun(self):
        """Debe aceptar nombres propios con mayúscula."""
        valid_messages = [
            "feat: add HDF5 compression",
            "fix: resolve API connection issue",
            "docs: update LLM audit policy",
            "feat: implement UUID generation"
        ]
        for message in valid_messages:
            is_valid, error = validate_commit_message(message)
            self.assertTrue(is_valid, f"Should accept: {message}")

    def test_merge_commit(self):
        """Debe aceptar merge commits."""
        message = "Merge branch 'feature/new-policy' into main"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_revert_commit(self):
        """Debe aceptar revert commits."""
        message = 'Revert "feat: add problematic feature"'
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_all_valid_types(self):
        """Debe aceptar todos los tipos válidos."""
        for commit_type in VALID_TYPES:
            message = f"{commit_type}: test message"
            is_valid, error = validate_commit_message(message)
            self.assertTrue(is_valid, f"Should accept type: {commit_type}")

    def test_scope_with_dash(self):
        """Debe aceptar scope con guión."""
        message = "feat(llm-audit): add new validator"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)

    def test_scope_with_underscore(self):
        """Debe aceptar scope con underscore."""
        message = "fix(corpus_ops): resolve append bug"
        is_valid, error = validate_commit_message(message)
        self.assertTrue(is_valid)


if __name__ == '__main__':
    unittest.main()
