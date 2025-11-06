"""Diarization service package - Post-processing speaker identification.

Complete speaker diarization solution with:
  - Speaker classification using Ollama (PACIENTE, MEDICO, DESCONOCIDO)
  - Text improvement (ortografía, gramática) via LLM
  - Job management (HDF5-backed)
  - Result assembly and export

Architecture:
  Input: Pre-transcribed segments (from TranscriptionService or corpus.h5)
  Processing: ONLY applies LLM for speaker + text improvement (no transcription)
  Output: Diarized segments with speaker labels and improved text

Structure:
  - service.py: Main DiarizationService class (orchestration only)
  - ollama.py: Ollama speaker classification and text improvement
  - jobs.py: HDF5-backed job state management
  - models.py: Dataclasses (DiarizationSegment, DiarizationResult, DiarizationJob)

Card: FI-BACKEND-FEAT-004 (refactored)
Created: 2025-11-05
"""

from __future__ import annotations

from backend.services.diarization.service import DiarizationService

__all__ = ["DiarizationService"]
