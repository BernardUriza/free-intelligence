"""
Admin API Module

RBAC-protected administrative endpoints.
Requires SUPERADMIN role for access.

Submodules:
- users: User management (CRUD, roles, blocking)
"""

from .users import router as users_router

__all__ = ["users_router"]
