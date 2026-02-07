"""Local authentication provider.

Implements IAuthProvider using LocalTokenService (HS256 JWTs).
Local JWT auth provider.
"""

from __future__ import annotations

import structlog

from ..domain import IAuthProvider, User, UserRole
from ..domain.constants import DEFAULT_ROLE_PERMISSIONS
from .local_token_service import LocalTokenService

logger = structlog.get_logger(__name__)


class LocalAuthProvider(IAuthProvider):
    """Self-hosted auth provider using HS256 JWT tokens."""

    def __init__(self, token_service: LocalTokenService) -> None:
        self.token_service = token_service

    async def validate_token(self, token: str) -> User | None:
        payload = await self.token_service.validate(token)

        roles = payload.roles or [UserRole.CLINICIAN]
        clinic_id = payload.claims.get("clinic_id") if payload.claims else None

        user = User(
            id=payload.subject,
            email=payload.email or "",
            roles=roles,
            tenant_id=payload.tenant_id,
            clinic_id=clinic_id,
            metadata={"claims": payload.claims},
            name=payload.claims.get("name") if payload.claims else None,
            username=payload.email,
        )

        logger.debug(
            "local_token_validated",
            user_id=user.id,
            clinic_id=clinic_id,
            roles=[role.value for role in user.roles],
        )

        return user

    async def get_user_roles(self, user_id: str) -> list[UserRole]:
        return []

    async def has_permission(self, user: User, permission: str) -> bool:
        if not permission:
            return True

        if any(role == UserRole.SUPERADMIN for role in user.roles):
            return True

        if permission in user.permissions:
            return True

        for role in user.roles:
            role_perms = DEFAULT_ROLE_PERMISSIONS.get(role, set())
            if "*" in role_perms or permission in role_perms:
                return True

        return False
