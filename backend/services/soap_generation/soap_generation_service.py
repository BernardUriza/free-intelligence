"""SOAP Generation Service - Main orchestrator.

This module coordinates the complete SOAP generation workflow,
orchestrating transcription reading, LLM extraction, model building,
and completeness scoring.

Refactored to use provider-agnostic LLM client (supports Claude, Ollama, OpenAI).
"""

from __future__ import annotations

from typing import Any

from backend.logger import get_logger
from backend.providers.models import SOAPNote

from .completeness import CompletenessCalculator
from .defaults import get_default_soap_structure
from .llm_client import LLMClient, SOAPExtractionError
from .reader import TranscriptionReader, TranscriptionReadError
from .soap_builder import SOAPBuilder, SOAPBuildError

__all__ = ["SOAPGenerationService"]

logger = get_logger(__name__)


class SOAPGenerationService:
    """Orchestrator for SOAP note generation from diarization transcriptions.

    Coordinates reading transcriptions from HDF5, extracting SOAP data
    from LLM (Claude/Ollama/OpenAI), building models, and calculating completeness scores.
    """

    def __init__(
        self,
        h5_path: str = "storage/diarization.h5",
        provider: str = "claude",
    ):
        """Initialize SOAP generation service.

        Args:
            h5_path: Path to diarization HDF5 file
            provider: LLM provider (claude, ollama, openai) - configured via fi.policy.yaml
        """
        self.reader = TranscriptionReader(h5_path)
        self.llm_client = LLMClient(provider=provider)
        self.provider = provider
        logger.info(
            "SOAPGenerationService initialized",
            h5_path=h5_path,
            provider=provider,
        )

    def generate_soap_for_job(self, job_id: str) -> SOAPNote:
        """Generate SOAP note from diarization job.

        Orchestrates the complete pipeline:
        1. Read transcription from HDF5
        2. Extract SOAP sections via LLM (Claude/Ollama/OpenAI)
        3. Build Pydantic models
        4. Calculate completeness score
        5. Return SOAPNote

        Args:
            job_id: Diarization job ID

        Returns:
            SOAPNote with structured medical data

        Raises:
            ValueError: If transcription is empty
            TranscriptionReadError: If HDF5 read fails
            SOAPExtractionError: If LLM extraction fails
            SOAPBuildError: If model building fails
        """
        try:
            # Step 1: Read transcription from HDF5
            logger.info(
                "SOAP_GENERATION_START",
                job_id=job_id,
                provider=self.provider,
            )
            transcription = self.reader.read(job_id)

            if not transcription:
                raise ValueError(f"No transcription found for job {job_id}")

            logger.info(
                "TRANSCRIPTION_READ_SUCCESS",
                job_id=job_id,
                length=len(transcription),
            )

            # Step 2: Extract SOAP sections via LLM
            logger.info(
                "SOAP_EXTRACTION_START",
                job_id=job_id,
                provider=self.provider,
            )
            soap_data = self._extract_soap_data(transcription)

            logger.info(
                "SOAP_EXTRACTION_SUCCESS",
                job_id=job_id,
                has_data=bool(soap_data),
            )

            # Step 3: Build SOAP models
            logger.info(
                "SOAP_MODEL_BUILD_START",
                job_id=job_id,
            )
            subjetivo, objetivo, analisis, plan = SOAPBuilder.build(job_id, soap_data)

            logger.info(
                "SOAP_MODEL_BUILD_SUCCESS",
                job_id=job_id,
            )

            # Step 4: Calculate completeness score
            completeness = CompletenessCalculator.calculate(subjetivo, objetivo, analisis, plan)

            # Step 5: Build complete SOAPNote
            logger.info(
                "SOAP_NOTE_BUILD_START",
                job_id=job_id,
                completeness=completeness,
            )
            soap_note = SOAPBuilder.build_note(
                job_id, subjetivo, objetivo, analisis, plan, completeness
            )

            logger.info(
                "SOAP_GENERATION_COMPLETED",
                job_id=job_id,
                completeness=soap_note.completeness,
                provider=self.provider,
            )

            return soap_note

        except (
            TranscriptionReadError,
            SOAPExtractionError,
            SOAPBuildError,
        ) as e:
            logger.error(
                "SOAP_GENERATION_FAILED",
                job_id=job_id,
                provider=self.provider,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        except Exception as e:
            logger.error(
                "SOAP_GENERATION_UNEXPECTED_ERROR",
                job_id=job_id,
                provider=self.provider,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _extract_soap_data(self, transcription: str) -> dict[str, Any]:
        """Extract SOAP data from transcription via LLM.

        Handles extraction errors gracefully by returning default structure.

        Args:
            transcription: Medical consultation transcription

        Returns:
            Dictionary with SOAP sections (default if extraction fails)
        """
        try:
            return self.llm_client.extract_soap(transcription)
        except SOAPExtractionError as e:
            logger.warning(
                "LLM_EXTRACTION_FAILED_USING_DEFAULTS",
                provider=self.provider,
                error=str(e),
            )
            # Return default structure on error
            return get_default_soap_structure()
