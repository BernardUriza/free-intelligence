"""Repository interfaces (ABCs)."""

from fi_storage.domain.interfaces.repositories import (
    ITaskRepository,
    ISessionRepository,
    IAudioRepository,
)

__all__ = ["ITaskRepository", "ISessionRepository", "IAudioRepository"]
