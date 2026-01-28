from __future__ import annotations

from .adapters.fastapi_adapter import (
    auth_router,
    get_current_user,
    require_permission,
    require_roles,
)
from .domain import (
    IAuthProvider,
    ITokenService,
    RefreshToken,
    TokenPayload,
    User,
    UserRole,
)
from .infrastructure.middleware.auth_middleware import set_auth_provider

__all__ = [
    "IAuthProvider",
    "ITokenService",
    "RefreshToken",
    "TokenPayload",
    "User",
    "UserRole",
    "auth_router",
    "get_current_user",
    "require_permission",
    "require_roles",
    "set_auth_provider",
]
