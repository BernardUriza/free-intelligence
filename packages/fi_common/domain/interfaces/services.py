from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class UseCase(ABC):
    """Base use-case interface."""

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - contract only
        raise NotImplementedError


__all__ = ["UseCase"]
