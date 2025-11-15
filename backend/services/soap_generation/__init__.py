"""SOAP Generation Package - Medical consultation SOAP note generation.

This package provides a modular, clean architecture for generating
SOAP (Subjective-Objective-Assessment-Plan) notes from diarization
transcriptions using LLM extraction.

Architecture:
    - soap_generation_service.py: Main orchestrator (SOAPGenerationService)
    - reader.py: HDF5 transcription I/O (TranscriptionReader)
    - llm_client.py: Provider-agnostic LLM interaction (LLMClient)
    - soap_builder.py: Pydantic model building (SOAPBuilder)
    - completeness.py: Scoring logic (CompletenessCalculator)
    - defaults.py: Fallback structures

Example usage:

    from backend.services.soap_generation import SOAPGenerationService

    service = SOAPGenerationService(
        h5_path="storage/diarization.h5",
        provider="claude"  # or "ollama", "openai"
    )

    soap_note = service.generate_soap_for_job(job_id="some-uuid")
    print(soap_note.completeness)
"""

from __future__ import annotations

from .completeness import CompletenessCalculator
from .defaults import get_default_soap_structure
from .llm_client import LLMClient, SOAPExtractionError
from .reader import TranscriptionReader, TranscriptionReadError
from .soap_builder import SOAPBuilder, SOAPBuildError
from .soap_generation_service import SOAPGenerationService
from .soap_models import (
    AssessmentData,
    ObjectiveData,
    PlanData,
    SOAPNote,
    SubjectiveData,
)

__all__ = [
    # Main service
    "SOAPGenerationService",
    # Utilities
    "TranscriptionReader",
    "LLMClient",
    "SOAPBuilder",
    "CompletenessCalculator",
    "get_default_soap_structure",
    # Exceptions
    "TranscriptionReadError",
    "SOAPExtractionError",
    "SOAPBuildError",
    # Models
    "SOAPNote",
    "SubjectiveData",
    "ObjectiveData",
    "AssessmentData",
    "PlanData",
]

__version__ = "2.0.0"  # Provider-agnostic refactor
__author__ = "Free Intelligence"
