from __future__ import annotations

from abc import ABC, abstractmethod

from ..entities.token import TokenPayload


class ITokenService(ABC):
    @abstractmethod
    async def validate(self, token: str) -> TokenPayload:
        raise NotImplementedError
