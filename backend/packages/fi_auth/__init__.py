from __future__ import annotations

from .adapters.fastapi_adapter import auth_router, get_current_user, require_permission, require_roles
from .domain import IAuthProvider, ITokenService, RefreshToken, TokenPayload, User, UserRole
from .infrastructure.middleware.auth_middleware import set_auth_provider

__all__ = [
    "auth_router",
    "get_current_user",
    "require_permission",
    "require_roles",
    "IAuthProvider",
    "ITokenService",
    "TokenPayload",
    "RefreshToken",
    "User",
    "UserRole",
    "set_auth_provider",
]
