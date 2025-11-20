"""
Admin User Management API

RBAC-protected endpoints for user administration.
Requires SUPERADMIN role.

Endpoints:
- GET    /api/internal/admin/users - List users
- GET    /api/internal/admin/users/{id} - Get user details
- POST   /api/internal/admin/users - Create user / Send invitation
- PUT    /api/internal/admin/users/{id} - Update user
- DELETE /api/internal/admin/users/{id} - Delete user
- PUT    /api/internal/admin/users/{id}/block - Block/unblock user
- PUT    /api/internal/admin/users/{id}/roles - Update user roles

Author: Bernard Uriza
Created: 2025-11-20
"""

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from backend.services.auth0_management import get_auth0_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class UserListResponse(BaseModel):
    """Response for list users endpoint"""

    users: list[dict]
    total: int
    page: int
    per_page: int


class CreateUserRequest(BaseModel):
    """Request to create new user"""

    email: EmailStr
    name: str | None = None
    password: str | None = None
    roles: list[str] = Field(default_factory=list)
    send_verification_email: bool = True


class UpdateUserRequest(BaseModel):
    """Request to update user"""

    name: str | None = None
    email: EmailStr | None = None
    email_verified: bool | None = None
    user_metadata: dict | None = None


class BlockUserRequest(BaseModel):
    """Request to block/unblock user"""

    blocked: bool


class UpdateRolesRequest(BaseModel):
    """Request to update user roles"""

    roles: list[str]


# ============================================================================
# RBAC DEPENDENCY
# ============================================================================


async def require_superadmin(authorization: str = Header(None)) -> dict:
    """
    Verify user has SUPERADMIN role via JWT token.

    Performs:
    1. Extract JWT token from Authorization header
    2. Verify token signature with Auth0 JWKS
    3. Check token expiration
    4. Verify 'https://aurity.app/roles' contains 'FI-superadmin'

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        dict: User information (user_id, email, roles)

    Raises:
        HTTPException: 401 if token missing/invalid, 403 if not superadmin
    """
    from backend.auth.jwt_verifier import get_jwt_verifier

    if not authorization:
        logger.warning("SUPERADMIN_AUTH_MISSING")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        logger.warning("SUPERADMIN_AUTH_INVALID_FORMAT")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <token>",
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        verifier = get_jwt_verifier()
        user = verifier.verify_superadmin(token)
        return user

    except ValueError as e:
        # JWT verification failed or not superadmin
        error_msg = str(e)

        if "expired" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please login again.",
            )
        elif "superadmin" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Superadmin role required.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {error_msg}",
            )

    except Exception as e:
        logger.error("SUPERADMIN_AUTH_ERROR", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error",
        )


# ============================================================================
# USER CRUD ENDPOINTS
# ============================================================================


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 0,
    per_page: int = 50,
    search: str | None = None,
    admin: dict = Depends(require_superadmin),
):
    """
    List all users with pagination and search.

    Query Parameters:
    - page: Page number (0-indexed)
    - per_page: Results per page (max 100)
    - search: Lucene search query (e.g., "email:*@hospital.com")

    Returns:
    - users: List of user objects
    - total: Total user count
    - page: Current page
    - per_page: Results per page
    """
    try:
        service = get_auth0_service()
        response = service.list_users(
            page=page,
            per_page=per_page,
            search=search,
        )

        # Enrich users with roles
        users_with_roles = []
        for user in response.get("users", []):
            try:
                roles = service.get_user_roles(user["user_id"])
                user["roles"] = [r.get("name") for r in roles]
            except Exception as e:
                logger.warning(
                    "FAILED_TO_GET_ROLES_FOR_USER",
                    user_id=user["user_id"],
                    error=str(e),
                )
                user["roles"] = []

            users_with_roles.append(user)

        return UserListResponse(
            users=users_with_roles,
            total=response.get("total", len(users_with_roles)),
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error("LIST_USERS_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {e!s}",
        )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    admin: dict = Depends(require_superadmin),
):
    """
    Get user details by ID.

    Path Parameters:
    - user_id: Auth0 user ID (e.g., "auth0|...")

    Returns:
    - User object with roles
    """
    try:
        service = get_auth0_service()
        user = service.get_user(user_id)

        # Add roles
        try:
            roles = service.get_user_roles(user_id)
            user["roles"] = [r.get("name") for r in roles]
        except Exception:
            user["roles"] = []

        return user

    except Exception as e:
        logger.error("GET_USER_FAILED", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found: {e!s}",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    admin: dict = Depends(require_superadmin),
):
    """
    Create new user and send invitation email.

    Body:
    - email: User email (required)
    - name: User display name (optional)
    - password: User password (optional, random if not provided)
    - roles: List of role names to assign (optional)
    - send_verification_email: Send verification email (default: true)

    Returns:
    - Created user object
    """
    try:
        service = get_auth0_service()

        # Create user
        user = service.create_user(
            email=request.email,
            name=request.name,
            password=request.password,
            send_verification_email=request.send_verification_email,
        )

        user_id = user["user_id"]

        # Assign roles if provided
        if request.roles:
            try:
                # Get all available roles
                all_roles = service.list_roles()
                role_id_map = {r["name"]: r["id"] for r in all_roles}

                # Find role IDs for requested role names
                role_ids = [
                    role_id_map[role_name]
                    for role_name in request.roles
                    if role_name in role_id_map
                ]

                if role_ids:
                    service.assign_roles(user_id, role_ids)
                    user["roles"] = request.roles
                else:
                    logger.warning(
                        "NO_VALID_ROLES_FOUND",
                        requested_roles=request.roles,
                        available_roles=list(role_id_map.keys()),
                    )
                    user["roles"] = []

            except Exception as e:
                logger.error(
                    "FAILED_TO_ASSIGN_ROLES_ON_CREATE",
                    user_id=user_id,
                    error=str(e),
                )
                user["roles"] = []
        else:
            user["roles"] = []

        logger.info(
            "USER_CREATED_VIA_API",
            user_id=user_id,
            email=request.email,
            admin_email=admin.get("email"),
        )

        return user

    except Exception as e:
        logger.error("CREATE_USER_FAILED", email=request.email, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {e!s}",
        )


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: dict = Depends(require_superadmin),
):
    """
    Update user attributes.

    Path Parameters:
    - user_id: Auth0 user ID

    Body:
    - name: New display name (optional)
    - email: New email (optional)
    - email_verified: Email verification status (optional)
    - user_metadata: Custom user metadata (optional)

    Returns:
    - Updated user object
    """
    try:
        service = get_auth0_service()

        # Build updates dict (only include provided fields)
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.email is not None:
            updates["email"] = request.email
        if request.email_verified is not None:
            updates["email_verified"] = request.email_verified
        if request.user_metadata is not None:
            updates["user_metadata"] = request.user_metadata

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update provided",
            )

        user = service.update_user(user_id, updates)

        logger.info(
            "USER_UPDATED_VIA_API",
            user_id=user_id,
            fields_updated=list(updates.keys()),
            admin_email=admin.get("email"),
        )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error("UPDATE_USER_FAILED", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {e!s}",
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: dict = Depends(require_superadmin),
):
    """
    Delete user permanently.

    Path Parameters:
    - user_id: Auth0 user ID

    Returns:
    - 204 No Content on success
    """
    try:
        service = get_auth0_service()
        service.delete_user(user_id)

        logger.warning(
            "USER_DELETED_VIA_API",
            user_id=user_id,
            admin_email=admin.get("email"),
        )

        return None

    except Exception as e:
        logger.error("DELETE_USER_FAILED", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {e!s}",
        )


# ============================================================================
# USER STATUS ENDPOINTS
# ============================================================================


@router.put("/{user_id}/block")
async def block_user(
    user_id: str,
    request: BlockUserRequest,
    admin: dict = Depends(require_superadmin),
):
    """
    Block or unblock a user.

    Path Parameters:
    - user_id: Auth0 user ID

    Body:
    - blocked: True to block, False to unblock

    Returns:
    - Updated user object
    """
    try:
        service = get_auth0_service()
        user = service.block_user(user_id, request.blocked)

        logger.warning(
            "USER_BLOCK_STATUS_CHANGED_VIA_API",
            user_id=user_id,
            blocked=request.blocked,
            admin_email=admin.get("email"),
        )

        return user

    except Exception as e:
        logger.error("BLOCK_USER_FAILED", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to block/unblock user: {e!s}",
        )


# ============================================================================
# ROLE MANAGEMENT ENDPOINTS
# ============================================================================


@router.put("/{user_id}/roles")
async def update_user_roles(
    user_id: str,
    request: UpdateRolesRequest,
    admin: dict = Depends(require_superadmin),
):
    """
    Replace user's roles with new set.

    Path Parameters:
    - user_id: Auth0 user ID

    Body:
    - roles: List of role names (replaces existing roles)

    Returns:
    - Updated user object with roles
    """
    try:
        service = get_auth0_service()

        # Get all available roles
        all_roles = service.list_roles()
        role_id_map = {r["name"]: r["id"] for r in all_roles}

        # Get current user roles
        current_roles = service.get_user_roles(user_id)
        current_role_ids = {r["id"] for r in current_roles}

        # Find role IDs for requested role names
        requested_role_ids = {
            role_id_map[role_name] for role_name in request.roles if role_name in role_id_map
        }

        # Calculate roles to add and remove
        roles_to_add = requested_role_ids - current_role_ids
        roles_to_remove = current_role_ids - requested_role_ids

        # Remove old roles
        if roles_to_remove:
            service.remove_roles(user_id, list(roles_to_remove))

        # Add new roles
        if roles_to_add:
            service.assign_roles(user_id, list(roles_to_add))

        # Get updated user with roles
        user = service.get_user(user_id)
        updated_roles = service.get_user_roles(user_id)
        user["roles"] = [r.get("name") for r in updated_roles]

        logger.info(
            "USER_ROLES_UPDATED_VIA_API",
            user_id=user_id,
            roles_added=len(roles_to_add),
            roles_removed=len(roles_to_remove),
            final_roles=user["roles"],
            admin_email=admin.get("email"),
        )

        return user

    except Exception as e:
        logger.error("UPDATE_ROLES_FAILED", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user roles: {e!s}",
        )


@router.get("/roles")
async def list_available_roles(
    admin: dict = Depends(require_superadmin),
):
    """
    List all available roles in the system.

    Returns:
    - List of role objects
    """
    try:
        service = get_auth0_service()
        roles = service.list_roles()

        return {"roles": roles}

    except Exception as e:
        logger.error("LIST_ROLES_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list roles: {e!s}",
        )
