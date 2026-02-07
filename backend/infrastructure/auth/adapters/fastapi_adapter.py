from __future__ import annotations

from ..domain import User, UserRole
from ..infrastructure.middleware import (
    get_current_user,
    get_optional_current_user,
    require_permission,
    require_roles,
)


def __getattr__(name: str):
    """Lazy-load auth_router to avoid importing SQLAlchemy models at module init."""
    if name == "auth_router":
        from ..api.auth_routes import auth_router

        return auth_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "User",
    "UserRole",
    "auth_router",
    "get_current_user",
    "get_optional_current_user",
    "require_permission",
    "require_roles",
]
