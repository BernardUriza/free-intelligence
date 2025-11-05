"""SOAP Generation Package - Medical consultation SOAP note generation.

This package provides a modular, clean architecture for generating
SOAP (Subjective-Objective-Assessment-Plan) notes from diarization
transcriptions using LLM extraction.

Architecture:
    - service.py: Main orchestrator (SOAPGenerationService)
    - reader.py: HDF5 transcription I/O (TranscriptionReader)
    - ollama_client.py: LLM interaction (OllamaClient)
    - soap_builder.py: Pydantic model building (SOAPBuilder)
    - completeness.py: Scoring logic (CompletenessCalculator)
    - defaults.py: Fallback structures

Example usage:

    from backend.services.soap_generation import SOAPGenerationService

    service = SOAPGenerationService(
        h5_path="storage/diarization.h5",
        ollama_base_url="http://localhost:11434",
        ollama_model="mistral"
    )

    soap_note = service.generate_soap_for_job(job_id="some-uuid")
    print(soap_note.completeness)
"""

from __future__ import annotations

from .completeness import CompletenessCalculator
from .defaults import get_default_soap_structure
from .ollama_client import OllamaClient, OllamaExtractionError
from .reader import TranscriptionReader, TranscriptionReadError
from .service import SOAPGenerationService
from .soap_builder import SOAPBuilder, SOAPBuildError

__all__ = [
    # Main service
    "SOAPGenerationService",
    # Utilities
    "TranscriptionReader",
    "OllamaClient",
    "SOAPBuilder",
    "CompletenessCalculator",
    "get_default_soap_structure",
    # Exceptions
    "TranscriptionReadError",
    "OllamaExtractionError",
    "SOAPBuildError",
]

__version__ = "1.0.0"
__author__ = "Free Intelligence"
