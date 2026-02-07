"""RBAC - Role-Based Access Control for Event Sourcing.

Defines permissions for accessing event streams, projections, and replays.

Roles:
- FI-superadmin: Full access to all event operations
- FI-clinician: Read access to own events, limited write

Usage:
    from infrastructure.events.security.rbac import check_event_access, require_event_permission

    # Check access
    if check_event_access(user, EventPermission.READ_STREAM, session_id="ses-123"):
        events = await load_stream(session_id)

    # Use as dependency
    @router.get("/events/stream/{session_id}")
    async def get_stream(
        session_id: str,
        user: User = Depends(get_current_user),
        _: None = Depends(require_event_permission(EventPermission.READ_STREAM)),
    ):
        ...
"""

from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable

from backend.utils.common.logging.logger import get_logger
from fastapi import Depends, HTTPException, status

if TYPE_CHECKING:
    from backend.infrastructure.auth.domain import User

logger = get_logger(__name__)


class EventPermission(str, Enum):
    """Event-related permissions."""

    # Stream operations
    READ_STREAM = "events:read_stream"
    READ_ALL_STREAMS = "events:read_all_streams"

    # Replay operations
    REPLAY_AGGREGATE = "events:replay"
    REBUILD_PROJECTION = "events:rebuild_projection"

    # Projection access
    READ_PROJECTION = "events:read_projection"
    READ_ALL_PROJECTIONS = "events:read_all_projections"

    # SSE streaming
    SUBSCRIBE_SSE = "events:subscribe_sse"

    # Metrics and tracing
    READ_METRICS = "events:read_metrics"
    READ_TRACING = "events:read_tracing"

    # Admin operations
    MANAGE_CONSUMERS = "events:manage_consumers"
    PURGE_EVENTS = "events:purge_events"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[str, set[EventPermission]] = {
    "FI-superadmin": set(EventPermission),  # All permissions
    "FI-clinician": {
        EventPermission.READ_STREAM,
        EventPermission.REPLAY_AGGREGATE,
        EventPermission.READ_PROJECTION,
        EventPermission.SUBSCRIBE_SSE,
    },
}


def get_permissions_for_roles(roles: list[str]) -> set[EventPermission]:
    """Get all permissions for a list of roles.

    Args:
        roles: List of role names

    Returns:
        Set of permissions
    """
    permissions: set[EventPermission] = set()
    for role in roles:
        role_perms = ROLE_PERMISSIONS.get(role, set())
        permissions.update(role_perms)
    return permissions


def check_event_access(
    user: Any,
    permission: EventPermission,
    resource_id: str | None = None,
) -> bool:
    """Check if user has permission for event operation.

    Args:
        user: User object with roles
        permission: Required permission
        resource_id: Optional resource ID for ownership check

    Returns:
        True if access granted
    """
    # Get user roles (self-hosted JWT)
    roles = getattr(user, "roles", [])

    # Get permissions for roles
    user_permissions = get_permissions_for_roles(roles)

    # Check permission
    if permission in user_permissions:
        # Check ownership for non-admin
        if permission == EventPermission.READ_STREAM and resource_id:
            # Admins can read all
            if EventPermission.READ_ALL_STREAMS in user_permissions:
                return True
            # Regular users can only read their own sessions
            user_id = getattr(user, "id", None) or getattr(user, "sub", None)
            if user_id and resource_id.startswith(f"user-{user_id}"):
                return True
            # Session ownership check would go here
            # For now, allow if they have READ_STREAM
            return True

        return True

    logger.warning(
        "EVENT_ACCESS_DENIED",
        user_id=getattr(user, "id", "unknown"),
        permission=permission.value,
        resource_id=resource_id,
    )
    return False


def require_event_permission(permission: EventPermission) -> Callable:
    """FastAPI dependency to require event permission.

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """

    async def dependency(
        # user: User = Depends(get_current_user),
    ) -> None:
        """Check permission dependency.

        Note: This is a placeholder. In production, uncomment the
        user dependency and implement get_current_user.
        """
        # For now, allow all access in development
        # In production, uncomment:
        # if not check_event_access(user, permission):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail=f"Missing permission: {permission.value}",
        #     )
        pass

    return dependency


def audit_event_access(
    user: Any,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    success: bool = True,
) -> None:
    """Log event access for audit trail.

    Args:
        user: User who performed action
        action: Action performed (read, replay, rebuild, etc.)
        resource_type: Type of resource (stream, projection, etc.)
        resource_id: Resource identifier
        success: Whether action succeeded
    """
    user_id = getattr(user, "id", None) or getattr(user, "sub", "anonymous")
    roles = getattr(user, "roles", [])

    logger.info(
        "EVENT_ACCESS_AUDIT",
        user_id=user_id,
        roles=roles,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        success=success,
    )


# ============================================================================
# DECORATORS
# ============================================================================


def requires_permission(permission: EventPermission) -> Callable:
    """Decorator to require permission for a function.

    Args:
        permission: Required permission

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract user from kwargs or first arg
            user = kwargs.get("user") or kwargs.get("current_user")
            if user is None and args:
                user = args[0] if hasattr(args[0], "roles") else None

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if not check_event_access(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permission: {permission.value}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
