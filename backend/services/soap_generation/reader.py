"""HDF5 transcription reader for diarization jobs.

This module handles reading transcriptions from HDF5 storage,
managing I/O operations and chunk concatenation.
"""

from __future__ import annotations

from typing import List, cast

import h5py

from backend.logger import get_logger

__all__ = ["TranscriptionReader", "TranscriptionReadError"]

logger = get_logger(__name__)


class TranscriptionReadError(Exception):
    """Raised when transcription cannot be read from HDF5."""

    pass


class TranscriptionReader:
    """Reads transcriptions from HDF5 diarization storage."""

    def __init__(self, h5_path: str = "storage/diarization.h5"):
        """Initialize transcription reader.

        Args:
            h5_path: Path to diarization HDF5 file
        """
        self.h5_path = h5_path
        logger.info("TranscriptionReader initialized", h5_path=h5_path)

    def read(self, job_id: str) -> str:
        """Read full transcription from HDF5 chunks.

        Args:
            job_id: Diarization job ID

        Returns:
            Concatenated transcription text

        Raises:
            TranscriptionReadError: If chunks not found or cannot be read
        """
        try:
            with h5py.File(self.h5_path, "r") as f:
                chunks_path = f"diarization/{job_id}/chunks"
                if chunks_path not in f:
                    raise TranscriptionReadError(f"No chunks found for job {job_id}")

                chunks_dataset = cast(h5py.Dataset, f[chunks_path])
                texts = self._extract_texts(chunks_dataset)

                transcription = " ".join(texts)
                dataset_length = len(chunks_dataset)  # type: ignore[arg-type]

                logger.info(
                    "TRANSCRIPTION_READ",
                    job_id=job_id,
                    chunks_count=dataset_length,
                    transcription_length=len(transcription),
                )

                return transcription

        except TranscriptionReadError:
            raise
        except Exception as e:
            logger.error("TRANSCRIPTION_READ_FAILED", job_id=job_id, error=str(e))
            raise TranscriptionReadError(
                f"Failed to read transcription for job {job_id}: {e!s}"
            ) from e

    def _extract_texts(self, chunks_dataset: h5py.Dataset) -> list[str]:
        """Extract text from chunks dataset.

        Args:
            chunks_dataset: HDF5 dataset containing chunk records

        Returns:
            List of non-empty text strings
        """
        texts: List[str] = []
        dataset_length = len(chunks_dataset)  # type: ignore[arg-type]

        for i in range(dataset_length):
            row = chunks_dataset[i]
            text = row["text"]

            # Handle bytes encoding
            if isinstance(text, bytes):
                text = text.decode("utf-8")

            # Add non-empty strings only
            if isinstance(text, str) and text.strip():
                texts.append(text)

        return texts
