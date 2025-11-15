"""Transcription reader for SOAP generation (Clean Architecture).

This module provides transcription reading through repository abstraction.
NO direct HDF5 access - delegates to SoapRepository.

Refactored: 2025-11-14 (Clean Architecture - Repository Pattern)
"""

from __future__ import annotations

from backend.logger import get_logger
from backend.repositories.soap_repository import (
    SoapRepository,
    TranscriptionNotFoundError,
)

__all__ = ["TranscriptionReader", "TranscriptionReadError"]

logger = get_logger(__name__)


class TranscriptionReadError(Exception):
    """Raised when transcription cannot be read."""

    pass


class TranscriptionReader:
    """Reads transcriptions via repository layer (Clean Architecture).

    NO direct HDF5 access - uses SoapRepository abstraction.
    """

    def __init__(self, repository: Optional[SoapRepository] = None):
        """Initialize transcription reader.

        Args:
            repository: SoapRepository instance (injected for testability)
        """
        self.repository = repository or SoapRepository()
        logger.info("TranscriptionReader initialized (using SoapRepository)")

    def read(self, job_id: str) -> str:
        """Read full transcription via repository.

        Args:
            job_id: Diarization job ID

        Returns:
            Concatenated transcription text

        Raises:
            TranscriptionReadError: If chunks not found or cannot be read
        """
        try:
            transcription = self.repository.get_transcription_text(job_id)
            logger.info(
                "TRANSCRIPTION_READ",
                job_id=job_id,
                transcription_length=len(transcription),
            )
            return transcription

        except TranscriptionNotFoundError as e:
            logger.error("TRANSCRIPTION_NOT_FOUND", job_id=job_id, error=str(e))
            raise TranscriptionReadError(str(e)) from e
        except Exception as e:
            logger.error("TRANSCRIPTION_READ_FAILED", job_id=job_id, error=str(e))
            raise TranscriptionReadError(
                f"Failed to read transcription for job {job_id}: {e!s}"
            ) from e
