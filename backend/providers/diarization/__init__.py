"""Speaker Diarization Provider Package.

Provides unified interface for speaker identification (who speaks when):
- Pyannote (local, offline, free)
- Azure GPT-4 (text-based LLM diarization)

Usage:
    from backend.providers.diarization import get_diarization_provider

    # Audio-based diarization
    provider = get_diarization_provider("pyannote")
    result = provider.diarize("audio.wav", num_speakers=2)

    # Text-based diarization
    provider = get_diarization_provider("azure_gpt4")
    result = provider.diarize_text(transcript, chunks=chunks)

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor from monolith)
"""

from backend.providers.diarization.base import (
    DiarizationProvider,
    DiarizationProviderType,
    TextBasedDiarizationProvider,
)
from backend.providers.diarization.factory import (
    get_diarization_provider,
    list_providers,
    register_provider,
)
from backend.providers.diarization.models import (
    DiarizationResponse,
    DiarizationSegment,
    Speaker,
)
from backend.providers.diarization.providers import (
    AzureGPT4Provider,
    PyannoteProvider,
)

__all__ = [
    # Models
    "DiarizationResponse",
    "DiarizationSegment",
    "Speaker",
    # Base classes
    "DiarizationProvider",
    "DiarizationProviderType",
    "TextBasedDiarizationProvider",
    # Providers
    "AzureGPT4Provider",
    "PyannoteProvider",
    # Factory
    "get_diarization_provider",
    "list_providers",
    "register_provider",
]
