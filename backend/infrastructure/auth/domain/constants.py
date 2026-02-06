"""Auth domain constants.

Role-permission mapping used by LocalAuthProvider and RBAC middleware.
Default role permissions (provider-agnostic).
"""

from __future__ import annotations

from .entities.user import UserRole

DEFAULT_ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPERADMIN: {"*"},
    UserRole.CLINICIAN: {"clinical:read", "clinical:write"},
}
