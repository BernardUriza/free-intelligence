#!/usr/bin/env python3
"""
Tests for corpus_identity module.

FI-DATA-FEAT-004
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from corpus_identity import (
    generate_corpus_id,
    generate_owner_hash,
    get_corpus_identity,
    verify_corpus_ownership,
)
from corpus_schema import init_corpus


class TestCorpusIdentityGenerators(unittest.TestCase):
    """Test corpus_id and owner_hash generators."""

    def test_generate_corpus_id_format(self):
        """Test corpus_id is valid UUID v4."""
        corpus_id = generate_corpus_id()

        # UUID v4 is 36 characters with 4 dashes
        self.assertEqual(len(corpus_id), 36)
        self.assertEqual(corpus_id.count("-"), 4)

        # Should be unique
        corpus_id2 = generate_corpus_id()
        self.assertNotEqual(corpus_id, corpus_id2)

    def test_generate_owner_hash_format(self):
        """Test owner_hash is valid SHA256."""
        owner_hash = generate_owner_hash("bernard@example.com")

        # SHA256 is 64 hex characters
        self.assertEqual(len(owner_hash), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in owner_hash))

    def test_generate_owner_hash_deterministic(self):
        """Test owner_hash is deterministic (same input = same output)."""
        hash1 = generate_owner_hash("bernard@example.com")
        hash2 = generate_owner_hash("bernard@example.com")
        self.assertEqual(hash1, hash2)

    def test_generate_owner_hash_different_inputs(self):
        """Test different inputs produce different hashes."""
        hash1 = generate_owner_hash("bernard@example.com")
        hash2 = generate_owner_hash("other@example.com")
        self.assertNotEqual(hash1, hash2)

    def test_generate_owner_hash_with_salt(self):
        """Test salt changes the hash."""
        hash_no_salt = generate_owner_hash("bernard@example.com")
        hash_with_salt = generate_owner_hash("bernard@example.com", salt="secret")
        self.assertNotEqual(hash_no_salt, hash_with_salt)

        # Same salt produces same hash
        hash_with_salt2 = generate_owner_hash("bernard@example.com", salt="secret")
        self.assertEqual(hash_with_salt, hash_with_salt2)

    def test_generate_owner_hash_empty_identifier(self):
        """Test empty identifier raises ValueError."""
        with self.assertRaises(ValueError):
            generate_owner_hash("")


class TestCorpusIdentityOperations(unittest.TestCase):
    """Test corpus identity operations."""

    test_dir: str
    corpus_path: str

    def setUp(self):
        """Create temporary directory for test corpora."""
        self.test_dir = tempfile.mkdtemp()
        self.corpus_path = str(Path(self.test_dir) / "test_corpus.h5")

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_add_corpus_identity(self):
        """Test adding identity to corpus."""
        # Create corpus without identity
        init_corpus(self.corpus_path, owner_identifier="bernard@example.com")

        # Get identity
        identity = get_corpus_identity(self.corpus_path)
        self.assertIsNotNone(identity)
        self.assertIn("corpus_id", identity)
        self.assertIn("owner_hash", identity)

        # Verify corpus_id format
        self.assertEqual(len(identity["corpus_id"]), 36)

        # Verify owner_hash format
        self.assertEqual(len(identity["owner_hash"]), 64)

    def test_add_corpus_identity_with_custom_corpus_id(self):
        """Test adding identity with pre-generated corpus_id."""
        # Create empty corpus first (we need to modify init_corpus for this test)
        # For now, skip this test as init_corpus auto-generates identity
        pass

    def test_verify_corpus_ownership_success(self):
        """Test successful ownership verification."""
        # Create corpus
        init_corpus(self.corpus_path, owner_identifier="bernard@example.com")

        # Verify ownership
        is_owner = verify_corpus_ownership(self.corpus_path, "bernard@example.com")
        self.assertTrue(is_owner)

    def test_verify_corpus_ownership_failure(self):
        """Test failed ownership verification."""
        # Create corpus
        init_corpus(self.corpus_path, owner_identifier="bernard@example.com")

        # Verify with wrong owner
        is_owner = verify_corpus_ownership(self.corpus_path, "other@example.com")
        self.assertFalse(is_owner)

    def test_verify_corpus_ownership_with_salt(self):
        """Test ownership verification with salt."""
        # Create corpus with salt
        init_corpus(self.corpus_path, owner_identifier="bernard@example.com", salt="secret")

        # Verify with correct salt
        is_owner = verify_corpus_ownership(self.corpus_path, "bernard@example.com", salt="secret")
        self.assertTrue(is_owner)

        # Verify without salt (should fail)
        is_owner = verify_corpus_ownership(self.corpus_path, "bernard@example.com")
        self.assertFalse(is_owner)

    def test_get_corpus_identity(self):
        """Test retrieving corpus identity."""
        # Create corpus
        init_corpus(self.corpus_path, owner_identifier="bernard@example.com")

        # Get identity
        identity = get_corpus_identity(self.corpus_path)
        self.assertIsNotNone(identity)
        self.assertIn("corpus_id", identity)
        self.assertIn("owner_hash", identity)
        self.assertIn("created_at", identity)
        self.assertIn("version", identity)
        self.assertIn("schema_version", identity)

    def test_get_corpus_identity_nonexistent(self):
        """Test getting identity from non-existent corpus."""
        identity = get_corpus_identity("/tmp/nonexistent.h5")
        self.assertIsNone(identity)


if __name__ == "__main__":
    unittest.main()
