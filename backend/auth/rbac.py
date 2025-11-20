"""
Free Intelligence - RBAC (Role-Based Access Control)
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI
Author: Bernard Uriza Orozco
Created: 2025-11-17

Role-based authorization logic for protecting ePHI endpoints.
HIPAA Reference: 45 CFR §164.308(a)(4) - Access Management
"""

from __future__ import annotations

from typing import List

from fastapi import HTTPException, status

from backend.auth.models import ROLE_PERMISSIONS, Permission, User, UserRole

# ============================================================================
# RBAC Permission Checks
# ============================================================================


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if a user has a specific permission based on their role.

    Args:
        user: User object with role
        permission: Permission to check

    Returns:
        True if user has permission, False otherwise

    Example:
        >>> user = User(role=UserRole.MEDICO, ...)
        >>> has_permission(user, Permission.WRITE)  # True
        >>> has_permission(user, Permission.DELETE)  # False
    """
    role_perms = ROLE_PERMISSIONS.get(user.role, [])
    return permission in role_perms


def require_permission(user: User, permission: Permission) -> None:
    """
    Require that a user has a specific permission, raise 403 if not.

    Args:
        user: User object with role
        permission: Required permission

    Raises:
        HTTPException: 403 Forbidden if user lacks permission

    Example:
        >>> require_permission(user, Permission.WRITE)  # OK for MEDICO
        >>> require_permission(nurse_user, Permission.WRITE)  # Raises 403
    """
    if not has_permission(user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User with role {user.role.value} does not have '{permission.value}' permission",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(user: User, allowed_roles: List[UserRole]) -> None:
    """
    Require that a user has one of the allowed roles, raise 403 if not.

    Args:
        user: User object with role
        allowed_roles: List of allowed roles

    Raises:
        HTTPException: 403 Forbidden if user's role is not in allowed_roles

    Example:
        >>> require_roles(user, [UserRole.MEDICO, UserRole.ADMIN])  # OK
        >>> require_roles(nurse_user, [UserRole.MEDICO])  # Raises 403
    """
    if user.role not in allowed_roles:
        allowed_roles_str = ", ".join([r.value for r in allowed_roles])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User with role {user.role.value} is not authorized. Allowed roles: {allowed_roles_str}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def can_modify_soap(user: User) -> bool:
    """
    Check if a user can modify SOAP notes (medical records).

    HIPAA Requirement: Only MEDICO and ADMIN can modify ePHI.
    ENFERMERA has read-only access.

    Args:
        user: User object with role

    Returns:
        True if user can modify SOAP, False otherwise
    """
    return user.role in [UserRole.MEDICO, UserRole.ADMIN]


def require_modify_soap(user: User) -> None:
    """
    Require that a user can modify SOAP notes, raise 403 if not.

    Args:
        user: User object with role

    Raises:
        HTTPException: 403 Forbidden if user cannot modify SOAP

    Example:
        >>> require_modify_soap(medico_user)  # OK
        >>> require_modify_soap(nurse_user)  # Raises 403
    """
    if not can_modify_soap(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User with role {user.role.value} cannot modify SOAP notes (read-only access)",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# RBAC Matrix Export
# ============================================================================


def export_rbac_matrix_csv() -> str:
    """
    Export RBAC matrix as CSV for HIPAA compliance evidence.

    Returns:
        CSV string with role, resource, action columns

    Example output:
        role,resource,action
        MEDICO,SOAP,read
        MEDICO,SOAP,write
        ENFERMERA,SOAP,read
        ADMIN,SOAP,read
        ADMIN,SOAP,write
        ADMIN,SOAP,delete
    """
    lines = ["role,resource,action"]

    for role, permissions in ROLE_PERMISSIONS.items():
        for perm in permissions:
            # Map permissions to resources
            if perm == Permission.READ:
                lines.append(f"{role.value},SOAP,read")
                lines.append(f"{role.value},Sessions,read")
            elif perm == Permission.WRITE:
                lines.append(f"{role.value},SOAP,write")
                lines.append(f"{role.value},Sessions,write")
            elif perm == Permission.DELETE:
                lines.append(f"{role.value},SOAP,delete")
                lines.append(f"{role.value},Sessions,delete")
            elif perm == Permission.ADMIN:
                lines.append(f"{role.value},System,admin")

    return "\n".join(lines)
