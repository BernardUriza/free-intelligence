"""SOAP Repository - Data access for SOAP generation.

Abstracts HDF5 access for SOAP generation service.
Provides clean data layer for transcription reading.

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Clean Architecture Refactor - Extract SoapRepository
"""

from __future__ import annotations

import h5py
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class TranscriptionNotFoundError(Exception):
    """Raised when transcription data not found in storage."""

    pass


class SoapRepository:
    """Repository for SOAP generation data access.

    Abstracts HDF5 operations for SOAP service layer.
    """

    def __init__(self, h5_path: str = "storage/diarization.h5"):
        """Initialize SOAP repository.

        Args:
            h5_path: Path to diarization HDF5 file
        """
        self.h5_path = h5_path
        logger.info("SoapRepository initialized", h5_path=h5_path)

    def get_transcription_text(self, job_id: str) -> str:
        """Get full transcription text for a job.

        Args:
            job_id: Diarization job identifier

        Returns:
            Concatenated transcription text

        Raises:
            TranscriptionNotFoundError: If job not found or no chunks
        """
        try:
            with h5py.File(self.h5_path, "r") as f:
                chunks_path = f"diarization/{job_id}/chunks"
                if chunks_path not in f:
                    raise TranscriptionNotFoundError(f"No chunks found for job {job_id}")

                chunks_dataset = f[chunks_path]
                texts = self._extract_texts_from_dataset(chunks_dataset)

                transcription = " ".join(texts)
                dataset_length = len(chunks_dataset)  # type: ignore[arg-type]

                logger.info(
                    "TRANSCRIPTION_FETCHED",
                    job_id=job_id,
                    chunks_count=dataset_length,
                    text_length=len(transcription),
                )

                return transcription

        except TranscriptionNotFoundError:
            raise
        except Exception as e:
            logger.error("TRANSCRIPTION_FETCH_FAILED", job_id=job_id, error=str(e))
            raise TranscriptionNotFoundError(
                f"Failed to fetch transcription for job {job_id}: {e!s}"
            ) from e

    def get_transcription_chunks(self, job_id: str) -> list[dict]:
        """Get individual transcription chunks for a job.

        Args:
            job_id: Diarization job identifier

        Returns:
            List of chunk dicts with text, timestamp, etc.

        Raises:
            TranscriptionNotFoundError: If job not found
        """
        try:
            with h5py.File(self.h5_path, "r") as f:
                chunks_path = f"diarization/{job_id}/chunks"
                if chunks_path not in f:
                    raise TranscriptionNotFoundError(f"No chunks found for job {job_id}")

                chunks_dataset = f[chunks_path]
                chunks = []

                dataset_length = len(chunks_dataset)  # type: ignore[arg-type]
                for i in range(dataset_length):
                    row = chunks_dataset[i]
                    text = row["text"]

                    # Handle bytes encoding
                    if isinstance(text, bytes):
                        text = text.decode("utf-8")

                    if isinstance(text, str) and text.strip():
                        chunks.append(
                            {
                                "index": i,
                                "text": text.strip(),
                                "timestamp": row.get("timestamp", 0.0),
                            }
                        )

                logger.info(
                    "CHUNKS_FETCHED",
                    job_id=job_id,
                    chunks_count=len(chunks),
                )

                return chunks

        except TranscriptionNotFoundError:
            raise
        except Exception as e:
            logger.error("CHUNKS_FETCH_FAILED", job_id=job_id, error=str(e))
            raise TranscriptionNotFoundError(
                f"Failed to fetch chunks for job {job_id}: {e!s}"
            ) from e

    def get_transcriptions_batch(
        self, job_ids: list[str]
    ) -> dict[str, str | None]:
        """Get transcriptions for multiple jobs in a single HDF5 operation.

        Performance optimization: Single file open for N job_ids vs N file opens.
        Eliminates N+1 query pattern when fetching transcriptions for multiple sessions.

        Args:
            job_ids: List of diarization job identifiers

        Returns:
            Dict mapping job_id → transcription text (None if job not found)

        Example:
            # BEFORE (N+1 queries):
            for job_id in job_ids:
                text = repo.get_transcription_text(job_id)  # Opens file N times

            # AFTER (Batch loading):
            results = repo.get_transcriptions_batch(job_ids)  # Opens file 1 time
            for job_id, text in results.items():
                if text is not None:
                    process(text)

        Note:
            Phase P4-3 Performance Optimization (Holoceno Tardío)
            Batch loading pattern to avoid N+1 queries.
        """
        results: dict[str, str | None] = {}

        try:
            with h5py.File(self.h5_path, "r") as f:
                for job_id in job_ids:
                    chunks_path = f"diarization/{job_id}/chunks"

                    if chunks_path not in f:
                        logger.warning(
                            "TRANSCRIPTION_NOT_FOUND_BATCH",
                            job_id=job_id,
                        )
                        results[job_id] = None
                        continue

                    chunks_dataset = f[chunks_path]
                    texts = self._extract_texts_from_dataset(chunks_dataset)
                    results[job_id] = " ".join(texts)

            found_count = sum(1 for v in results.values() if v is not None)
            logger.info(
                "TRANSCRIPTIONS_BATCH_FETCHED",
                total_requested=len(job_ids),
                found=found_count,
                not_found=len(job_ids) - found_count,
            )

            return results

        except Exception as e:
            logger.error("TRANSCRIPTIONS_BATCH_FAILED", error=str(e))
            # Return partial results on error
            return {job_id: None for job_id in job_ids}

    def _extract_texts_from_dataset(self, chunks_dataset: h5py.Dataset) -> list[str]:
        """Extract text strings from HDF5 chunks dataset.

        Args:
            chunks_dataset: HDF5 dataset with chunk records

        Returns:
            List of non-empty text strings
        """
        texts: list[str] = []
        dataset_length = len(chunks_dataset)  # type: ignore[arg-type]

        for i in range(dataset_length):
            row = chunks_dataset[i]
            text = row["text"]

            # Handle bytes encoding
            if isinstance(text, bytes):
                text = text.decode("utf-8")

            # Add non-empty strings only
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())

        return texts
