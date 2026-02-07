from __future__ import annotations

from .domain import (
    IAuthProvider,
    ITokenService,
    RefreshToken,
    TokenPayload,
    User,
    UserRole,
)
from .infrastructure.middleware.auth_middleware import set_auth_provider
from .infrastructure.middleware import (
    get_current_user,
    get_optional_current_user,
    require_permission,
    require_roles,
)
from .utils.clinic_access import (
    validate_clinic_access,
    validate_doctor_access,
    validate_session_access,
)


def __getattr__(name: str):
    """Lazy-load auth_router to avoid importing SQLAlchemy models at package init."""
    if name == "auth_router":
        from .api.auth_routes import auth_router

        return auth_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "IAuthProvider",
    "ITokenService",
    "RefreshToken",
    "TokenPayload",
    "User",
    "UserRole",
    "auth_router",
    "get_current_user",
    "get_optional_current_user",
    "require_permission",
    "require_roles",
    "set_auth_provider",
    "validate_clinic_access",
    "validate_doctor_access",
    "validate_session_access",
]
