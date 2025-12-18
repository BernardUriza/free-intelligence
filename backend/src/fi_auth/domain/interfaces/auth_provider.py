from __future__ import annotations

from abc import ABC, abstractmethod

from ..entities.user import User, UserRole


class IAuthProvider(ABC):
    @abstractmethod
    async def validate_token(self, token: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> list[UserRole]:
        raise NotImplementedError

    @abstractmethod
    async def has_permission(self, user: User, permission: str) -> bool:
        raise NotImplementedError
