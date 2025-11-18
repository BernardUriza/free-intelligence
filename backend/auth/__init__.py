"""
Free Intelligence - Authentication Module
HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration

This module provides Auth0 authentication and RBAC for HIPAA compliance.

**Auth Flow:**
1. Frontend redirects to Auth0 Universal Login
2. User authenticates (username/password, MFA, social login)
3. Auth0 redirects back with authorization code
4. Frontend exchanges code for access_token
5. Frontend sends access_token in Authorization: Bearer header
6. Backend validates token with Auth0 JWKS

Usage:
    from backend.auth import get_current_user_auth0, User

    @app.get("/protected")
    async def protected_endpoint(user: User = Depends(get_current_user_auth0)):
        return {"user": user.username, "role": user.role}
"""
from backend.auth.auth0_dependencies import (
    get_current_user_auth0,
    require_admin_auth0,
    require_medico_auth0,
)
from backend.auth.auth0_router import router as auth_router
from backend.auth.models import Permission, User, UserRole

__all__ = [
    "User",
    "UserRole",
    "Permission",
    "get_current_user_auth0",
    "require_admin_auth0",
    "require_medico_auth0",
    "auth_router",
]
