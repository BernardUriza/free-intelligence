from __future__ import annotations

import structlog

from ...domain import IAuthProvider, User, UserRole
from ...domain.interfaces.token_service import ITokenService
from .auth0_config import Auth0Config

logger = structlog.get_logger(__name__)

DEFAULT_ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPERADMIN: {"*"},
    UserRole.ADMIN: {"admin:read", "admin:write"},
    UserRole.CLINICIAN: {"clinical:read", "clinical:write"},
    UserRole.PATIENT: {"patient:read"},
    UserRole.LEGACY_ADMIN: {"admin:read", "admin:write"},
    UserRole.LEGACY_MEDICO: {"clinical:read", "clinical:write"},
    UserRole.LEGACY_NURSE: {"clinical:read"},
}


class Auth0Provider(IAuthProvider):
    def __init__(self, config: Auth0Config, token_service: ITokenService):
        self.config = config
        self.token_service = token_service

    async def validate_token(self, token: str) -> User | None:
        payload = await self.token_service.validate(token)

        roles = payload.roles or [UserRole.CLINICIAN]
        user = User(
            id=payload.subject,
            email=payload.email or "",
            roles=roles,
            tenant_id=payload.tenant_id,
            metadata={"claims": payload.claims},
            name=payload.claims.get("name") if payload.claims else None,
            username=payload.claims.get("nickname") if payload.claims else payload.email,
        )

        logger.debug(
            "auth0_token_validated",
            user_id=user.id,
            roles=[role.value for role in user.roles],
            issuer=payload.issuer,
        )

        return user

    async def get_user_roles(self, user_id: str) -> list[UserRole]:
        logger.info("auth0_roles_lookup_not_configured", user_id=user_id)
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
