"""Checkpoint Ports - Abstract Interfaces (Hexagonal Architecture).

Ports define the contracts between the application core and external world.
They are abstract interfaces that adapters must implement.

Types of Ports:
- Primary (Driving): Used by external actors to interact with the application
- Secondary (Driven): Used by the application to interact with external services

No implementations here - only Protocol definitions.
"""

from .audio_concatenator import AudioConcatenatorPort
from .audio_repository import AudioRepositoryPort

__all__ = [
    "AudioConcatenatorPort",
    "AudioRepositoryPort",
]
