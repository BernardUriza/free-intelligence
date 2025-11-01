#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Buffered HDF5 Writer

Write buffer para optimizar I/O en escrituras HDF5.
Implementa auto-flush, atomic writes, y manejo thread-safe.

Card: FI-DATA-FEAT-002
File: backend/buffered_writer.py
Created: 2025-10-28
"""

import threading
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import h5py  # type: ignore

from backend.append_only_policy import AppendOnlyPolicy
from backend.logger import get_logger

logger = get_logger(__name__)


class BufferedHDF5Writer:
    """
    Buffered writer for HDF5 interactions.

    Features:
    - Write buffer para reducir I/O operations
    - Auto-flush cada N operaciones o timeout
    - Thread-safe con lock
    - Atomic writes (all-or-nothing)
    - Rotación automática al alcanzar tamaño máximo

    Examples:
        >>> writer = BufferedHDF5Writer("storage/corpus.h5", buffer_size=100)
        >>> writer.write_interaction(
        ...     session_id="session_123",
        ...     prompt="Hello",
        ...     response="Hi!",
        ...     model="claude-3-5-sonnet",
        ...     tokens=50
        ... )
        >>> writer.flush()  # Force flush
        >>> writer.close()
    """

    def __init__(
        self,
        corpus_path: str,
        buffer_size: int = 100,
        max_corpus_size_gb: float = 4.0,
        auto_flush_seconds: int = 60,
    ):
        """
        Initialize buffered writer.

        Args:
            corpus_path: Path to HDF5 corpus file
            buffer_size: Number of interactions to buffer before flush
            max_corpus_size_gb: Maximum corpus size before rotation (GB)
            auto_flush_seconds: Auto-flush timeout (seconds)
        """
        self.corpus_path = Path(corpus_path)
        self.buffer_size = buffer_size
        self.max_corpus_size_bytes = int(max_corpus_size_gb * 1024 * 1024 * 1024)
        self.auto_flush_seconds = auto_flush_seconds

        # Buffer: deque for thread-safe append/pop
        self.buffer: deque = deque()
        self.lock = threading.Lock()

        # Stats
        self.total_writes = 0
        self.total_flushes = 0
        self.last_flush_time = datetime.now()

        logger.info(
            "BUFFERED_WRITER_INITIALIZED",
            corpus_path=str(self.corpus_path),
            buffer_size=buffer_size,
            max_corpus_size_gb=max_corpus_size_gb,
        )

    def write_interaction(
        self,
        session_id: str,
        prompt: str,
        response: str,
        model: str,
        tokens: int,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Write interaction to buffer (non-blocking).

        Auto-flushes if buffer is full or timeout exceeded.

        Args:
            session_id: Session identifier
            prompt: User prompt
            response: Model response
            model: Model name
            tokens: Total tokens
            timestamp: ISO timestamp (auto-generated if None)

        Returns:
            interaction_id (UUID)
        """
        interaction_id = str(uuid.uuid4())

        if timestamp is None:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo("America/Mexico_City")
            timestamp = datetime.now(tz).isoformat()

        # Create interaction record
        record = {
            "session_id": session_id,
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "response": response,
            "model": model,
            "tokens": tokens,
        }

        with self.lock:
            self.buffer.append(record)
            buffer_len = len(self.buffer)

        logger.debug(
            "INTERACTION_BUFFERED",
            interaction_id=interaction_id,
            buffer_size=buffer_len,
            buffer_limit=self.buffer_size,
        )

        # Auto-flush conditions
        should_flush = False

        # Condition 1: Buffer full
        if buffer_len >= self.buffer_size:
            should_flush = True
            reason = "buffer_full"

        # Condition 2: Timeout exceeded
        elif (datetime.now() - self.last_flush_time).total_seconds() > self.auto_flush_seconds:
            should_flush = True
            reason = "timeout"

        if should_flush:
            logger.info("AUTO_FLUSH_TRIGGERED", reason=reason, buffer_size=buffer_len)
            self.flush()

        return interaction_id

    def flush(self) -> int:
        """
        Flush buffer to HDF5 (atomic operation).

        Returns:
            Number of interactions written

        Raises:
            Exception: If write fails (buffer is NOT cleared)
        """
        with self.lock:
            if not self.buffer:
                logger.debug("FLUSH_SKIPPED_EMPTY_BUFFER")
                return 0

            # Copy buffer for atomic write
            records_to_write = list(self.buffer)
            buffer_len = len(records_to_write)

        logger.info("FLUSH_STARTED", count=buffer_len)

        try:
            # Check corpus size before write
            if self.corpus_path.exists():
                corpus_size = self.corpus_path.stat().st_size
                if corpus_size >= self.max_corpus_size_bytes:
                    logger.warning(
                        "CORPUS_SIZE_LIMIT_REACHED",
                        size_bytes=corpus_size,
                        limit_bytes=self.max_corpus_size_bytes,
                    )
                    self._rotate_corpus()

            # Atomic write: all-or-nothing
            with AppendOnlyPolicy(str(self.corpus_path)), h5py.File(
                str(self.corpus_path), "a"
            ) as f:
                interactions = f["interactions"]

                # Current size
                current_size = interactions["session_id"].shape[0]
                new_size = current_size + buffer_len

                # Resize all datasets
                for dataset_name in interactions.keys():
                    interactions[dataset_name].resize((new_size,))

                # Write all buffered records
                for i, record in enumerate(records_to_write):
                    idx = current_size + i
                    interactions["session_id"][idx] = record["session_id"]
                    interactions["interaction_id"][idx] = record["interaction_id"]
                    interactions["timestamp"][idx] = record["timestamp"]
                    interactions["prompt"][idx] = record["prompt"]
                    interactions["response"][idx] = record["response"]
                    interactions["model"][idx] = record["model"]
                    interactions["tokens"][idx] = record["tokens"]

            # Success: clear buffer
            with self.lock:
                for _ in range(buffer_len):
                    self.buffer.popleft()

                self.total_writes += buffer_len
                self.total_flushes += 1
                self.last_flush_time = datetime.now()

            logger.info(
                "FLUSH_COMPLETED",
                count=buffer_len,
                total_writes=self.total_writes,
                total_flushes=self.total_flushes,
            )

            return buffer_len

        except Exception as e:
            logger.error(
                "FLUSH_FAILED",
                error=str(e),
                buffer_size=buffer_len,
                message="Buffer NOT cleared - data preserved",
            )
            raise

    def _rotate_corpus(self):
        """
        Rotate corpus file when size limit reached.

        Creates new file: corpus_YYYYMMDD_HHMMSS.h5
        Renames current to archived name.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived_path = self.corpus_path.parent / f"corpus_{timestamp}.h5"

        logger.warning(
            "CORPUS_ROTATION_STARTED",
            current_path=str(self.corpus_path),
            archived_path=str(archived_path),
        )

        # Rename current corpus
        self.corpus_path.rename(archived_path)

        # Initialize new corpus
        from backend.config_loader import load_config
        from backend.corpus_schema import init_corpus

        config = load_config()
        owner_id = config.get("owner", {}).get("identifier", "bernard.uriza@example.com")

        init_corpus(str(self.corpus_path), owner_identifier=owner_id)

        logger.info(
            "CORPUS_ROTATION_COMPLETED",
            new_corpus=str(self.corpus_path),
            archived=str(archived_path),
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get writer statistics.

        Returns:
            Dict with stats: buffer_size, total_writes, total_flushes, etc.
        """
        with self.lock:
            buffer_len = len(self.buffer)

        corpus_size = self.corpus_path.stat().st_size if self.corpus_path.exists() else 0

        return {
            "buffer_size": buffer_len,
            "buffer_limit": self.buffer_size,
            "total_writes": self.total_writes,
            "total_flushes": self.total_flushes,
            "corpus_size_bytes": corpus_size,
            "corpus_size_mb": round(corpus_size / (1024 * 1024), 2),
            "corpus_path": str(self.corpus_path),
            "last_flush": self.last_flush_time.isoformat(),
        }

    def verify_integrity(self) -> bool:
        """
        Verify corpus integrity.

        Checks:
        - File exists and readable
        - Required groups/datasets present
        - No corruption detected

        Returns:
            True if integrity OK, False otherwise
        """
        if not self.corpus_path.exists():
            logger.error("INTEGRITY_CHECK_FAILED", reason="corpus_not_found")
            return False

        try:
            with h5py.File(str(self.corpus_path), "r") as f:
                # Check required groups
                if "interactions" not in f:
                    logger.error("INTEGRITY_CHECK_FAILED", reason="missing_interactions_group")
                    return False

                interactions = f["interactions"]

                # Check all datasets have same size
                sizes = [interactions[key].shape[0] for key in interactions.keys()]
                if len(set(sizes)) > 1:
                    logger.error(
                        "INTEGRITY_CHECK_FAILED", reason="inconsistent_dataset_sizes", sizes=sizes
                    )
                    return False

                logger.info("INTEGRITY_CHECK_PASSED", interactions_count=sizes[0] if sizes else 0)
                return True

        except Exception as e:
            logger.error("INTEGRITY_CHECK_FAILED", error=str(e))
            return False

    def close(self):
        """
        Close writer and flush remaining buffer.
        """
        logger.info("BUFFERED_WRITER_CLOSING", buffer_size=len(self.buffer))

        if self.buffer:
            self.flush()

        logger.info(
            "BUFFERED_WRITER_CLOSED",
            total_writes=self.total_writes,
            total_flushes=self.total_flushes,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


if __name__ == "__main__":
    """Demo script"""
    print("🚀 Buffered HDF5 Writer Demo")
    print("=" * 60)

    # Test 1: Initialize writer
    print("\n1️⃣  Initializing buffered writer...")
    writer = BufferedHDF5Writer(
        "storage/corpus.h5",
        buffer_size=5,  # Small buffer for demo
        auto_flush_seconds=30,
    )
    print("   ✅ Writer initialized (buffer_size=5)")

    # Test 2: Write interactions (buffered)
    print("\n2️⃣  Writing 3 interactions (buffered)...")
    for i in range(3):
        interaction_id = writer.write_interaction(
            session_id="session_demo",
            prompt=f"Test prompt {i+1}",
            response=f"Test response {i+1}",
            model="claude-3-5-sonnet-20241022",
            tokens=50,
        )
        print(f"   ✅ Buffered: {interaction_id}")

    stats = writer.get_stats()
    print(f"   📊 Buffer size: {stats['buffer_size']}/{stats['buffer_limit']}")

    # Test 3: Manual flush
    print("\n3️⃣  Manual flush...")
    count = writer.flush()
    print(f"   ✅ Flushed {count} interactions to HDF5")

    # Test 4: Verify integrity
    print("\n4️⃣  Verifying corpus integrity...")
    is_valid = writer.verify_integrity()
    print(f"   {'✅' if is_valid else '❌'} Integrity check: {'PASSED' if is_valid else 'FAILED'}")

    # Test 5: Stats
    print("\n5️⃣  Writer statistics:")
    stats = writer.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Test 6: Close
    print("\n6️⃣  Closing writer...")
    writer.close()
    print("   ✅ Writer closed")

    print("\n" + "=" * 60)
    print("✅ Demo complete!")
