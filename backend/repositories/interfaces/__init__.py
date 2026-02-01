"""Repository interfaces for Clean Architecture.

Defines abstract contracts that decouple business logic from infrastructure.
All repository implementations must satisfy these interfaces.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - True Dependency Injection
"""

from .iaudio_chunk_repository import IAudioChunkRepository
from .imemory_store import IMemoryStore
from .itask_repository import ITaskRepository

__all__ = [
    "IAudioChunkRepository",
    "IMemoryStore",
    "ITaskRepository",
]
