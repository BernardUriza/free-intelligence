#!/usr/bin/env python3
"""
Tests for Append-Only Policy Enforcement

FI-DATA-FEAT-005
"""

import os
import sys
import tempfile
import unittest

import h5py
import numpy as np

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from append_only_policy import (
    AppendOnlyPolicy,
    AppendOnlyViolation,
    get_dataset_size,
    verify_append_only_operation,
)
from corpus_ops import append_embedding, append_interaction
from corpus_schema import init_corpus


class TestAppendOnlyPolicy(unittest.TestCase):
    """Test append-only policy enforcement."""

    temp_dir: str
    corpus_path: str

    def setUp(self) -> None:
        """Create temporary corpus for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.corpus_path = os.path.join(self.temp_dir, "test_corpus.h5")

        # Initialize corpus with identity
        init_corpus(self.corpus_path, owner_identifier="test@example.com")

    def tearDown(self) -> None:
        """Clean up temporary files."""
        if os.path.exists(self.corpus_path):
            os.remove(self.corpus_path)
        os.rmdir(self.temp_dir)

    def test_context_manager_init(self) -> None:
        """Test AppendOnlyPolicy context manager initialization."""
        with AppendOnlyPolicy(self.corpus_path) as policy:
            # Should record original sizes
            self.assertGreater(len(policy.original_sizes), 0)
            self.assertIn("interactions/session_id", policy.original_sizes)
            self.assertIn("embeddings/interaction_id", policy.original_sizes)

    def test_context_manager_nonexistent_file(self) -> None:
        """Test policy with nonexistent corpus."""
        with self.assertRaises(FileNotFoundError):
            with AppendOnlyPolicy("/nonexistent/corpus.h5"):
                pass

    def test_append_interaction_allowed(self) -> None:
        """Test that appending interaction is allowed."""
        # Should not raise AppendOnlyViolation
        interaction_id = append_interaction(
            self.corpus_path, "session_test", "Test prompt", "Test response", "test-model", 100
        )
        self.assertIsNotNone(interaction_id)

    def test_append_embedding_allowed(self) -> None:
        """Test that appending embedding is allowed."""
        # First add interaction
        interaction_id = append_interaction(
            self.corpus_path, "session_test", "Test prompt", "Test response", "test-model", 100
        )

        # Then add embedding
        vector = np.random.rand(768).astype(np.float32)
        result = append_embedding(self.corpus_path, interaction_id, vector)
        self.assertTrue(result)

    def test_direct_mutation_blocked(self) -> None:
        """Test that direct mutation is blocked by policy."""
        # Add an interaction first
        append_interaction(
            self.corpus_path,
            "session_test",
            "Original prompt",
            "Original response",
            "test-model",
            100,
        )

        # Try to mutate existing data directly
        with self.assertRaises(AppendOnlyViolation):
            with AppendOnlyPolicy(self.corpus_path) as policy:
                # Attempt to modify existing data (index 0)
                policy.validate_write_index("interactions", "session_id", 0)

    def test_validate_write_index_existing(self) -> None:
        """Test validation of write to existing index."""
        # Add an interaction
        append_interaction(
            self.corpus_path, "session_test", "Test prompt", "Test response", "test-model", 100
        )

        with AppendOnlyPolicy(self.corpus_path) as policy:
            # Writing to existing index (0) should be rejected
            with self.assertRaises(AppendOnlyViolation) as context:
                policy.validate_write_index("interactions", "session_id", 0)

            self.assertIn("Cannot modify existing data", str(context.exception))

    def test_validate_write_index_new(self) -> None:
        """Test validation of write to new index."""
        # Add an interaction
        append_interaction(
            self.corpus_path, "session_test", "Test prompt", "Test response", "test-model", 100
        )

        with AppendOnlyPolicy(self.corpus_path) as policy:
            # Get current size
            current_size = get_dataset_size(self.corpus_path, "interactions", "session_id")

            # Writing to new index should be allowed
            result = policy.validate_write_index("interactions", "session_id", current_size)
            self.assertTrue(result)

    def test_validate_resize_increase(self) -> None:
        """Test validation of dataset size increase."""
        with AppendOnlyPolicy(self.corpus_path) as policy:
            original_size = get_dataset_size(self.corpus_path, "interactions", "session_id")

            # Increasing size should be allowed
            result = policy.validate_resize("interactions", "session_id", original_size + 10)
            self.assertTrue(result)

    def test_validate_resize_decrease(self) -> None:
        """Test validation of dataset size decrease."""
        # Add an interaction
        append_interaction(
            self.corpus_path, "session_test", "Test prompt", "Test response", "test-model", 100
        )

        with AppendOnlyPolicy(self.corpus_path) as policy:
            original_size = get_dataset_size(self.corpus_path, "interactions", "session_id")

            # Decreasing size should be rejected
            with self.assertRaises(AppendOnlyViolation) as context:
                policy.validate_resize("interactions", "session_id", original_size - 1)

            self.assertIn("Cannot shrink dataset", str(context.exception))

    def test_verify_operation_read(self) -> None:
        """Test verification of read operations."""
        result = verify_append_only_operation(self.corpus_path, "read_interactions", "interactions")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "read operation")

    def test_verify_operation_get(self) -> None:
        """Test verification of get operations."""
        result = verify_append_only_operation(self.corpus_path, "get_corpus_stats", "metadata")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "read operation")

    def test_verify_operation_append(self) -> None:
        """Test verification of append operations."""
        result = verify_append_only_operation(
            self.corpus_path, "append_interaction", "interactions", "session_id"
        )
        self.assertTrue(result["allowed"])
        self.assertEqual(result["reason"], "append operation")

    def test_verify_operation_mutation(self) -> None:
        """Test verification rejects mutation operations."""
        result = verify_append_only_operation(
            self.corpus_path, "update_interaction", "interactions", "prompt"
        )
        self.assertFalse(result["allowed"])
        self.assertIn("violates append-only policy", result["reason"])

    def test_verify_operation_delete(self) -> None:
        """Test verification rejects delete operations."""
        result = verify_append_only_operation(
            self.corpus_path, "delete_interaction", "interactions", "session_id"
        )
        self.assertFalse(result["allowed"])

    def test_get_dataset_size(self) -> None:
        """Test getting dataset size."""
        # Initial size should be 0
        size = get_dataset_size(self.corpus_path, "interactions", "session_id")
        self.assertEqual(size, 0)

        # Add interaction
        append_interaction(
            self.corpus_path, "session_test", "Test prompt", "Test response", "test-model", 100
        )

        # Size should be 1
        size = get_dataset_size(self.corpus_path, "interactions", "session_id")
        self.assertEqual(size, 1)

    def test_multiple_appends_allowed(self) -> None:
        """Test that multiple sequential appends are allowed."""
        # Should be able to append multiple times
        for i in range(5):
            interaction_id = append_interaction(
                self.corpus_path,
                f"session_test_{i}",
                f"Test prompt {i}",
                f"Test response {i}",
                "test-model",
                100 + i,
            )
            self.assertIsNotNone(interaction_id)

        # Verify all were added
        size = get_dataset_size(self.corpus_path, "interactions", "session_id")
        self.assertEqual(size, 5)

    def test_policy_exit_verification(self) -> None:
        """Test that policy verifies on exit."""
        # Normal append should exit cleanly
        with AppendOnlyPolicy(self.corpus_path):
            with h5py.File(self.corpus_path, "a") as f:
                interactions = f["interactions"]
                current_size = interactions["session_id"].shape[0]
                new_size = current_size + 1

                # Resize (increase)
                for dataset_name in interactions.keys():
                    interactions[dataset_name].resize((new_size,))

        # If we get here, exit verification passed

    def test_error_message_clarity(self) -> None:
        """Test that error messages are clear and actionable."""
        with AppendOnlyPolicy(self.corpus_path) as policy:
            try:
                policy.validate_write_index("interactions", "session_id", 0)
            except AppendOnlyViolation as e:
                error_msg = str(e)
                # Should contain key information
                self.assertIn("Cannot modify existing data", error_msg)
                self.assertIn("interactions/session_id", error_msg)
                self.assertIn("Append-only policy", error_msg)


if __name__ == "__main__":
    unittest.main()
