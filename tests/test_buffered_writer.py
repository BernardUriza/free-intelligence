"""
Test suite for buffered_writer.py

Validates buffer operations, auto-flush, rotation, and integrity checks
"""
import os
import shutil
import sys
import tempfile
import unittest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from buffered_writer import BufferedHDF5Writer
from corpus_schema import init_corpus


class TestBufferedHDF5Writer(unittest.TestCase):
    """Test buffered HDF5 writer"""

    def setUp(self):
        """Create temporary corpus for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.corpus_path = os.path.join(self.test_dir, "test_corpus.h5")

        # Initialize corpus
        init_corpus(self.corpus_path, owner_identifier="test@example.com")

    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir)

    def test_writer_initialization(self):
        """Test: Writer initializes correctly"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        self.assertEqual(writer.buffer_size, 10)
        self.assertEqual(len(writer.buffer), 0)
        self.assertEqual(writer.total_writes, 0)

        writer.close()

    def test_write_interaction_buffered(self):
        """Test: Interaction is buffered (not flushed immediately)"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        interaction_id = writer.write_interaction(
            session_id="session_test",
            prompt="Test prompt",
            response="Test response",
            model="test-model",
            tokens=50,
        )

        self.assertIsNotNone(interaction_id)
        self.assertEqual(len(writer.buffer), 1)
        self.assertEqual(writer.total_writes, 0)  # Not flushed yet

        writer.close()

    def test_manual_flush(self):
        """Test: Manual flush writes buffer to HDF5"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        # Write 3 interactions
        for i in range(3):
            writer.write_interaction(
                session_id="session_test",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=50,
            )

        self.assertEqual(len(writer.buffer), 3)

        # Flush
        count = writer.flush()

        self.assertEqual(count, 3)
        self.assertEqual(len(writer.buffer), 0)
        self.assertEqual(writer.total_writes, 3)
        self.assertEqual(writer.total_flushes, 1)

        writer.close()

    def test_auto_flush_buffer_full(self):
        """Test: Auto-flush when buffer is full"""
        writer = BufferedHDF5Writer(
            self.corpus_path,
            buffer_size=5,  # Small buffer
        )

        # Write 5 interactions (should trigger auto-flush)
        for i in range(5):
            writer.write_interaction(
                session_id="session_test",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=50,
            )

        # Buffer should be empty after auto-flush
        self.assertEqual(len(writer.buffer), 0)
        self.assertEqual(writer.total_writes, 5)
        self.assertEqual(writer.total_flushes, 1)

        writer.close()

    def test_flush_empty_buffer(self):
        """Test: Flush empty buffer is no-op"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        count = writer.flush()

        self.assertEqual(count, 0)
        self.assertEqual(writer.total_flushes, 0)

        writer.close()

    def test_get_stats(self):
        """Test: Get writer statistics"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        # Write 2 interactions
        for i in range(2):
            writer.write_interaction(
                session_id="session_test",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=50,
            )

        stats = writer.get_stats()

        self.assertEqual(stats["buffer_size"], 2)
        self.assertEqual(stats["buffer_limit"], 10)
        self.assertEqual(stats["total_writes"], 0)  # Not flushed yet
        self.assertIn("corpus_size_bytes", stats)
        self.assertIn("corpus_path", stats)

        writer.close()

    def test_verify_integrity_success(self):
        """Test: Integrity check passes for valid corpus"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        # Write and flush
        writer.write_interaction(
            session_id="session_test", prompt="Test", response="Test", model="test-model", tokens=50
        )
        writer.flush()

        # Verify integrity
        is_valid = writer.verify_integrity()

        self.assertTrue(is_valid)

        writer.close()

    def test_verify_integrity_missing_corpus(self):
        """Test: Integrity check fails for missing corpus"""
        nonexistent_path = os.path.join(self.test_dir, "nonexistent.h5")
        writer = BufferedHDF5Writer(nonexistent_path, buffer_size=10)

        is_valid = writer.verify_integrity()

        self.assertFalse(is_valid)

        writer.close()

    def test_context_manager(self):
        """Test: Context manager auto-flushes on exit"""
        with BufferedHDF5Writer(self.corpus_path, buffer_size=10) as writer:
            for i in range(3):
                writer.write_interaction(
                    session_id="session_test",
                    prompt=f"Prompt {i}",
                    response=f"Response {i}",
                    model="test-model",
                    tokens=50,
                )

            # Still buffered
            self.assertEqual(len(writer.buffer), 3)

        # After context exit, should be flushed
        # (can't check writer.buffer after close, but verify corpus has data)
        import h5py

        with h5py.File(self.corpus_path, "r") as f:
            interactions = f["interactions"]
            size = interactions["session_id"].shape[0]
            # Should have 3 interactions (excluding any initial data)
            self.assertGreaterEqual(size, 3)

    def test_close_flushes_buffer(self):
        """Test: Close() flushes remaining buffer"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        # Write 2 interactions
        for i in range(2):
            writer.write_interaction(
                session_id="session_test",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=50,
            )

        self.assertEqual(len(writer.buffer), 2)

        # Close should flush
        writer.close()

        # Verify data was written
        import h5py

        with h5py.File(self.corpus_path, "r") as f:
            interactions = f["interactions"]
            size = interactions["session_id"].shape[0]
            self.assertGreaterEqual(size, 2)

    def test_thread_safety_lock(self):
        """Test: Lock prevents concurrent writes"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        # Acquire lock
        writer.lock.acquire()

        # Lock should be held
        self.assertFalse(writer.lock.acquire(blocking=False))

        # Release lock
        writer.lock.release()

        # Now should be acquirable
        self.assertTrue(writer.lock.acquire(blocking=False))
        writer.lock.release()

        writer.close()

    def test_atomic_write_all_or_nothing(self):
        """Test: Flush is atomic (all records or none)"""
        writer = BufferedHDF5Writer(self.corpus_path, buffer_size=10)

        # Write 3 interactions
        for i in range(3):
            writer.write_interaction(
                session_id="session_test",
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="test-model",
                tokens=50,
            )

        # Get initial corpus size
        import h5py

        with h5py.File(self.corpus_path, "r") as f:
            initial_size = f["interactions"]["session_id"].shape[0]

        # Flush
        writer.flush()

        # Verify all 3 written
        with h5py.File(self.corpus_path, "r") as f:
            final_size = f["interactions"]["session_id"].shape[0]
            self.assertEqual(final_size - initial_size, 3)

        writer.close()


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
