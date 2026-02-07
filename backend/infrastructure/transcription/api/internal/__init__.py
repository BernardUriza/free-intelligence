"""Transcription Internal API.

Internal endpoints for transcription and diarization.

Routers:
- transcribe_router: Audio chunk upload and job status
- diarization_router: Diarization job status
"""

from .diarization import router as diarization_router
from .transcribe import router as transcribe_router

__all__ = ["transcribe_router", "diarization_router"]
