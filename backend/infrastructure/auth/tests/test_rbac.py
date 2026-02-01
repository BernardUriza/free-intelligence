from __future__ import annotations

import pytest
from backend.infrastructure.auth.domain.entities.user import User, UserRole
from backend.infrastructure.auth.infrastructure.middleware.rbac_middleware import (
    require_permission,
    require_roles,
)
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_require_roles_allows_primary_role():
    user = User(id="user-1", email="user@example.com", roles=[UserRole.SUPERADMIN])
    dependency = require_roles([UserRole.SUPERADMIN])

    resolved = await dependency(user=user)
    assert resolved is user


@pytest.mark.asyncio
async def test_require_roles_blocks_when_missing():
    user = User(id="user-1", email="user@example.com", roles=[UserRole.PATIENT])
    dependency = require_roles([UserRole.ADMIN])

    with pytest.raises(HTTPException):
        await dependency(user=user)


class _AllowAllProvider:
    async def has_permission(self, user: User, permission: str) -> bool:
        return True


class _DenyProvider:
    async def has_permission(self, user: User, permission: str) -> bool:
        return False


@pytest.mark.asyncio
async def test_require_permission_allows_when_provider_accepts():
    user = User(id="user-1", email="user@example.com", roles=[UserRole.ADMIN])
    dependency = require_permission("admin:write")

    resolved = await dependency(user=user, provider=_AllowAllProvider())
    assert resolved is user


@pytest.mark.asyncio
async def test_require_permission_blocks_when_provider_rejects():
    user = User(id="user-1", email="user@example.com", roles=[UserRole.ADMIN])
    dependency = require_permission("admin:write")

    with pytest.raises(HTTPException):
        await dependency(user=user, provider=_DenyProvider())
