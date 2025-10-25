#!/usr/bin/env python3
"""
Unit tests for corpus operations (append, read, stats).

FI-DATA-OPS (Test)
"""

import unittest
import tempfile
import sys
import numpy as np
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from corpus_schema import init_corpus
from corpus_ops import (
    append_interaction,
    append_embedding,
    get_corpus_stats,
    read_interactions
)


class TestCorpusOps(unittest.TestCase):
    """Test suite for corpus operations."""

    temp_file: tempfile._TemporaryFileWrapper  # type: ignore
    temp_path: str

    def setUp(self):
        """Create temporary corpus for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.h5', delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        Path(self.temp_path).unlink()

        # Initialize corpus
        init_corpus(self.temp_path, owner_identifier="test@example.com")

    def tearDown(self):
        """Clean up temporary file."""
        if Path(self.temp_path).exists():
            Path(self.temp_path).unlink()

    def test_append_interaction(self):
        """Test appending interaction to corpus."""
        interaction_id = append_interaction(
            self.temp_path,
            session_id="test_session_001",
            prompt="Test prompt",
            response="Test response",
            model="test-model",
            tokens=50,
            timestamp="2025-10-24T23:00:00-06:00"
        )

        self.assertIsNotNone(interaction_id)
        self.assertTrue(len(interaction_id) > 0)

    def test_append_multiple_interactions(self):
        """Test appending multiple interactions."""
        for i in range(5):
            interaction_id = append_interaction(
                self.temp_path,
                session_id=f"test_session_{i:03d}",
                prompt=f"Test prompt {i}",
                response=f"Test response {i}",
                model="test-model",
                tokens=50 + i
            )
            self.assertIsNotNone(interaction_id)

        # Verify count
        stats = get_corpus_stats(self.temp_path)
        self.assertEqual(stats["interactions_count"], 5)

    def test_append_embedding(self):
        """Test appending embedding vector."""
        # First append interaction
        interaction_id = append_interaction(
            self.temp_path,
            session_id="test_session",
            prompt="Test",
            response="Response",
            model="test-model",
            tokens=50
        )

        # Append embedding
        vector = np.random.rand(768).astype(np.float32)
        success = append_embedding(
            self.temp_path,
            interaction_id=interaction_id,
            vector=vector
        )

        self.assertTrue(success)

        # Verify count
        stats = get_corpus_stats(self.temp_path)
        self.assertEqual(stats["embeddings_count"], 1)

    def test_append_embedding_wrong_dimension(self):
        """Test that wrong dimension raises error."""
        interaction_id = "test_id"
        vector = np.random.rand(512).astype(np.float32)  # Wrong dim

        with self.assertRaises(ValueError):
            append_embedding(self.temp_path, interaction_id, vector)

    def test_get_corpus_stats(self):
        """Test getting corpus statistics."""
        stats = get_corpus_stats(self.temp_path)

        self.assertIn("interactions_count", stats)
        self.assertIn("embeddings_count", stats)
        self.assertIn("file_size_bytes", stats)
        self.assertIn("file_size_mb", stats)
        self.assertIn("created_at", stats)
        self.assertIn("version", stats)

        # Initial counts should be 0
        self.assertEqual(stats["interactions_count"], 0)
        self.assertEqual(stats["embeddings_count"], 0)

    def test_read_interactions(self):
        """Test reading interactions from corpus."""
        # Add some interactions
        for i in range(3):
            append_interaction(
                self.temp_path,
                session_id=f"session_{i}",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=100 + i
            )

        # Read them back
        interactions = read_interactions(self.temp_path, limit=10)

        self.assertEqual(len(interactions), 3)
        self.assertEqual(interactions[0]["prompt"], "Prompt 0")
        self.assertEqual(interactions[1]["response"], "Response 1")
        self.assertEqual(interactions[2]["tokens"], 102)

    def test_read_interactions_with_limit(self):
        """Test reading with limit."""
        # Add 5 interactions
        for i in range(5):
            append_interaction(
                self.temp_path,
                session_id="session",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=100
            )

        # Read only last 2
        interactions = read_interactions(self.temp_path, limit=2)

        self.assertEqual(len(interactions), 2)
        self.assertEqual(interactions[0]["prompt"], "Prompt 3")
        self.assertEqual(interactions[1]["prompt"], "Prompt 4")

    def test_read_interactions_empty_corpus(self):
        """Test reading from empty corpus."""
        interactions = read_interactions(self.temp_path)
        self.assertEqual(len(interactions), 0)


if __name__ == "__main__":
    unittest.main()
