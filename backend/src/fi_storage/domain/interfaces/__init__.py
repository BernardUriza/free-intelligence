"""Repository interfaces (ABCs)."""

from fi_storage.domain.interfaces.repositories import (
    IAudioRepository,
    ISessionRepository,
    ITaskRepository,
)

__all__ = ["IAudioRepository", "ISessionRepository", "ITaskRepository"]
