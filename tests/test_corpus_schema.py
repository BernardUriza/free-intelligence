#!/usr/bin/env python3
"""
Unit tests for HDF5 corpus schema.

Tests cover:
1. Corpus initialization with required groups
2. Schema validation
3. Dataset structure verification
4. Config integration

FI-DATA-FEAT-001
"""

import sys
import tempfile
import unittest
from pathlib import Path

import h5py

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from corpus_schema import CorpusSchema, init_corpus, validate_corpus


class TestCorpusSchema(unittest.TestCase):
    """Test suite for HDF5 corpus schema."""

    temp_file: tempfile._TemporaryFileWrapper  # type: ignore
    temp_path: str

    def setUp(self) -> None:
        """Create temporary file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()
        Path(self.temp_path).unlink()  # Remove it, will be created by tests

    def tearDown(self) -> None:
        """Clean up temporary file."""
        if Path(self.temp_path).exists():
            Path(self.temp_path).unlink()

    def test_init_corpus_creates_file(self) -> None:
        """Test that init_corpus creates HDF5 file."""
        success = init_corpus(self.temp_path, owner_identifier="test@example.com")
        self.assertTrue(success)
        self.assertTrue(Path(self.temp_path).exists())

    def test_init_corpus_creates_required_groups(self) -> None:
        """Test that all required groups are created."""
        init_corpus(self.temp_path, owner_identifier="test@example.com")

        with h5py.File(self.temp_path, "r") as f:
            for group in CorpusSchema.REQUIRED_GROUPS:
                self.assertIn(group, f, f"Group /{group} not found")

    def test_interactions_datasets(self) -> None:
        """Test that /interactions/ has all required datasets."""
        init_corpus(self.temp_path, owner_identifier="test@example.com")

        with h5py.File(self.temp_path, "r") as f:
            interactions = f["interactions"]
            for dataset_name in CorpusSchema.INTERACTION_DATASETS:
                self.assertIn(
                    dataset_name, interactions, f"Dataset /interactions/{dataset_name} not found"
                )

    def test_embeddings_datasets(self) -> None:
        """Test that /embeddings/ has all required datasets."""
        init_corpus(self.temp_path, owner_identifier="test@example.com")

        with h5py.File(self.temp_path, "r") as f:
            embeddings = f["embeddings"]
            for dataset_name in CorpusSchema.EMBEDDING_DATASETS:
                self.assertIn(
                    dataset_name, embeddings, f"Dataset /embeddings/{dataset_name} not found"
                )

            # Check vector dimensions (768-dim)
            self.assertEqual(embeddings["vector"].shape[1], 768)

    def test_metadata_attributes(self) -> None:
        """Test that /metadata/ has required attributes."""
        init_corpus(self.temp_path, owner_identifier="test@example.com")

        with h5py.File(self.temp_path, "r") as f:
            metadata = f["metadata"]
            self.assertIn("created_at", metadata.attrs)
            self.assertIn("version", metadata.attrs)
            self.assertIn("schema_version", metadata.attrs)

    def test_validate_corpus_valid(self) -> None:
        """Test validation of valid corpus."""
        init_corpus(self.temp_path, owner_identifier="test@example.com")
        result = validate_corpus(self.temp_path)

        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(result["path"], self.temp_path)

    def test_validate_corpus_missing_file(self) -> None:
        """Test validation of non-existent file."""
        result = validate_corpus("/nonexistent/corpus.h5")

        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("not found", result["errors"][0].lower())

    def test_validate_corpus_missing_group(self) -> None:
        """Test validation detects missing groups."""
        # Create incomplete corpus
        with h5py.File(self.temp_path, "w") as f:
            f.create_group("interactions")
            # Missing: embeddings, metadata

        errors = CorpusSchema.validate(self.temp_path)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("embeddings" in err for err in errors))
        self.assertTrue(any("metadata" in err for err in errors))

    def test_init_corpus_force_overwrite(self) -> None:
        """Test force overwrite of existing corpus."""
        # Create initial corpus
        init_corpus(self.temp_path, owner_identifier="test@example.com")

        # Should raise error without force
        with self.assertRaises(FileExistsError):
            init_corpus(self.temp_path, owner_identifier="test@example.com", force=False)

        # Should succeed with force
        success = init_corpus(self.temp_path, owner_identifier="test@example.com", force=True)
        self.assertTrue(success)

    def test_datasets_are_resizable(self) -> None:
        """Test that datasets are created with maxshape=None for appending."""
        init_corpus(self.temp_path, owner_identifier="test@example.com")

        with h5py.File(self.temp_path, "r") as f:
            # Check interactions datasets are resizable
            for dataset_name in CorpusSchema.INTERACTION_DATASETS:
                dataset = f["interactions"][dataset_name]
                self.assertEqual(dataset.maxshape, (None,), f"Dataset {dataset_name} not resizable")

            # Check embeddings datasets are resizable
            self.assertEqual(f["embeddings"]["interaction_id"].maxshape, (None,))
            self.assertEqual(f["embeddings"]["vector"].maxshape, (None, 768))


if __name__ == "__main__":
    unittest.main()
