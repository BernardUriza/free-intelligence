from __future__ import annotations

from fastapi import Depends, HTTPException, status

from ...domain import User, UserRole
from .auth_middleware import get_auth_provider, get_current_user


def require_roles(required_roles: list[UserRole]):
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no roles",
            )

        for role in user.roles:
            if role in required_roles:
                return user

        allowed = ", ".join([r.value for r in required_roles])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Required roles: {allowed}",
        )

    return _dependency


def require_permission(permission: str):
    async def _dependency(
        user: User = Depends(get_current_user),
        provider=Depends(get_auth_provider),
    ) -> User:
        if await provider.has_permission(user, permission):
            return user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return _dependency
