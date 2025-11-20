"""
Free Intelligence - Auth0 Token Validator
HIPAA Card: G-003 - Auth0 OAuth2/OIDC Integration
Author: Bernard Uriza Orozco
Created: 2025-11-17

Validates Auth0 JWT tokens using JWKS (JSON Web Key Set).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

import requests
from jose import JWTError, jwt

from backend.auth.auth0_config import (
    ALGORITHMS,
    AUTH0_API_IDENTIFIER,
    ISSUER,
    JWKS_URL,
    ROLES_CLAIM_KEY,
)
from backend.auth.models import UserRole

# ============================================================================
# JWKS Cache (Auth0 Public Keys)
# ============================================================================


@lru_cache(maxsize=1)
def get_jwks() -> Dict[str, Any]:
    """
    Fetch Auth0's JSON Web Key Set (public keys for token verification).

    Cached to avoid hitting Auth0's JWKS endpoint on every request.
    Cache is invalidated on server restart.

    Returns:
        JWKS dictionary with public keys

    Raises:
        Exception: If JWKS fetch fails
    """
    try:
        response = requests.get(JWKS_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to fetch JWKS from Auth0: {e}")


def get_signing_key(token: str) -> str:
    """
    Get the signing key from JWKS that matches the token's kid (key ID).

    Args:
        token: JWT token string

    Returns:
        PEM-formatted public key

    Raises:
        Exception: If signing key is not found
    """
    # Decode token header without verification to get kid (key ID)
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    if not kid:
        raise Exception("Token header missing 'kid' (key ID)")

    # Get JWKS and find matching key
    jwks = get_jwks()

    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            # Convert JWK to PEM format
            return jwt.algorithms.RSAAlgorithm.from_jwk(key)

    raise Exception(f"Signing key with kid '{kid}' not found in JWKS")


# ============================================================================
# Token Validation
# ============================================================================


def verify_auth0_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode an Auth0 JWT token.

    Validates:
    - Token signature (using Auth0's public key)
    - Token expiration
    - Issuer (must be Auth0)
    - Audience (must be our API identifier)

    Args:
        token: JWT token string (from Authorization: Bearer header)

    Returns:
        Decoded token payload (claims) including:
        - sub: User ID (Auth0 user_id)
        - email: User email
        - roles: Custom claim with user roles
        - permissions: Custom claim with permissions

    Raises:
        JWTError: If token is invalid, expired, or signature verification fails
        Exception: If JWKS fetch fails or signing key not found

    Example:
        >>> claims = verify_auth0_token("eyJ0eXAiOiJKV1QiLCJhbGc...")
        >>> print(claims["sub"])  # auth0|507f1f77bcf86cd799439011
        >>> print(claims["email"])  # doctor@hospital.com
        >>> print(claims["https://aurity.app/roles"])  # ["MEDICO"]
    """
    try:
        # Get the signing key (Auth0 public key)
        signing_key = get_signing_key(token)

        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=ALGORITHMS,
            audience=AUTH0_API_IDENTIFIER,
            issuer=ISSUER,
        )

        return payload

    except JWTError as e:
        raise JWTError(f"Invalid Auth0 token: {e}")
    except Exception as e:
        raise Exception(f"Token validation error: {e}")


def extract_user_roles(claims: Dict[str, Any]) -> list[UserRole]:
    """
    Extract user roles from Auth0 token claims.

    Auth0 stores custom claims with namespaced keys:
    - "https://aurity.app/roles": ["MEDICO", "ADMIN"]

    Args:
        claims: Decoded JWT token payload

    Returns:
        List of UserRole enums

    Example:
        >>> claims = {"https://aurity.app/roles": ["MEDICO"]}
        >>> extract_user_roles(claims)
        [<UserRole.MEDICO: 'MEDICO'>]
    """
    roles_list = claims.get(ROLES_CLAIM_KEY, [])

    # Convert string roles to UserRole enums
    user_roles = []
    for role_str in roles_list:
        try:
            user_roles.append(UserRole(role_str))
        except ValueError:
            # Skip invalid roles
            continue

    # Default to ENFERMERA (read-only) if no roles specified
    if not user_roles:
        user_roles = [UserRole.ENFERMERA]

    return user_roles


def extract_user_id(claims: Dict[str, Any]) -> str:
    """
    Extract Auth0 user ID from token claims.

    Auth0 user IDs have format: "auth0|507f1f77bcf86cd799439011"
    or "google-oauth2|123456789" for social logins.

    Args:
        claims: Decoded JWT token payload

    Returns:
        Auth0 user ID (sub claim)
    """
    return claims.get("sub", "")


def extract_user_email(claims: Dict[str, Any]) -> str | None:
    """
    Extract user email from token claims.

    Args:
        claims: Decoded JWT token payload

    Returns:
        User email or None
    """
    return claims.get("email")
