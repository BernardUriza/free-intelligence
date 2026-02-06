from __future__ import annotations

from .fastapi_adapter import (
    get_current_user,
    require_permission,
    require_roles,
)


def __getattr__(name: str):
    """Lazy-load auth_router to avoid importing SQLAlchemy models at package init."""
    if name == "auth_router":
        from .fastapi_adapter import auth_router

        return auth_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["auth_router", "get_current_user", "require_permission", "require_roles"]
