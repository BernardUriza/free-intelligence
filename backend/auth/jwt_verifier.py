"""
Auth0 JWT Token Verification

Verifies JWT tokens issued by Auth0 using JWKS (JSON Web Key Set).
Ensures tokens are valid, not expired, and contain required claims.

Security Features:
- Signature verification using Auth0 public keys
- Audience verification (prevents token reuse across apps)
- Issuer verification (prevents tokens from other Auth0 tenants)
- Expiration checking
- Role-based access control via custom claims

Author: Bernard Uriza
Created: 2025-11-20
"""

import os
from typing import Dict, Optional
from functools import lru_cache

import requests
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
import structlog

logger = structlog.get_logger(__name__)

# Auth0 configuration from environment
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_API_IDENTIFIER = os.getenv(
    "AUTH0_API_IDENTIFIER", "https://api.fi-aurity.duckdns.org"
)
AUTH0_ALGORITHMS = ["RS256"]  # Auth0 uses RS256 for signing
ROLES_CLAIM_NAMESPACE = "https://aurity.app/roles"


class Auth0JWTVerifier:
    """Verify Auth0 JWT tokens using JWKS"""

    def __init__(self):
        if not AUTH0_DOMAIN:
            raise ValueError("AUTH0_DOMAIN environment variable not set")

        self.domain = AUTH0_DOMAIN
        self.api_identifier = AUTH0_API_IDENTIFIER
        self.issuer = f"https://{AUTH0_DOMAIN}/"
        self.jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"

        logger.info(
            "JWT_VERIFIER_INITIALIZED",
            domain=self.domain,
            issuer=self.issuer,
            audience=self.api_identifier,
        )

    @lru_cache(maxsize=1)
    def get_jwks(self) -> Dict:
        """
        Fetch JWKS (JSON Web Key Set) from Auth0.

        Cached to avoid repeated network calls.
        Auth0 rotates keys infrequently, so cache is safe.

        Returns:
            dict: JWKS response containing public keys
        """
        try:
            response = requests.get(self.jwks_url, timeout=10)
            response.raise_for_status()
            jwks = response.json()

            logger.debug("JWKS_FETCHED", keys_count=len(jwks.get("keys", [])))
            return jwks

        except Exception as e:
            logger.error("JWKS_FETCH_FAILED", error=str(e))
            raise ValueError(f"Failed to fetch JWKS from Auth0: {str(e)}")

    def get_signing_key(self, token: str) -> str:
        """
        Get the signing key for a token from JWKS.

        Args:
            token: JWT token string

        Returns:
            str: PEM-formatted public key for verification

        Raises:
            ValueError: If key not found in JWKS
        """
        try:
            # Decode header without verification to get key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise ValueError("Token header missing 'kid' (key ID)")

            # Find matching key in JWKS
            jwks = self.get_jwks()
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    # Convert JWK to PEM
                    from jose.backends.cryptography_backend import CryptographyRSAKey

                    return CryptographyRSAKey(key, algorithm="RS256")

            raise ValueError(f"No matching key found in JWKS for kid: {kid}")

        except Exception as e:
            logger.error("SIGNING_KEY_ERROR", error=str(e))
            raise ValueError(f"Failed to get signing key: {str(e)}")

    def verify_token(self, token: str) -> Dict:
        """
        Verify JWT token and return decoded payload.

        Performs:
        1. Signature verification using JWKS
        2. Expiration check
        3. Issuer verification
        4. Audience verification

        Args:
            token: JWT token string

        Returns:
            dict: Decoded token payload

        Raises:
            ValueError: If token is invalid
            ExpiredSignatureError: If token is expired
            JWTClaimsError: If claims are invalid
        """
        try:
            # Get signing key from JWKS
            signing_key = self.get_signing_key(token)

            # Verify and decode token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=AUTH0_ALGORITHMS,
                audience=self.api_identifier,
                issuer=self.issuer,
            )

            logger.debug(
                "TOKEN_VERIFIED",
                sub=payload.get("sub"),
                exp=payload.get("exp"),
            )

            return payload

        except ExpiredSignatureError:
            logger.warning("TOKEN_EXPIRED")
            raise ValueError("Token has expired")

        except JWTClaimsError as e:
            logger.warning("TOKEN_CLAIMS_INVALID", error=str(e))
            raise ValueError(f"Token claims are invalid: {str(e)}")

        except JWTError as e:
            logger.warning("TOKEN_VERIFICATION_FAILED", error=str(e))
            raise ValueError(f"Token verification failed: {str(e)}")

        except Exception as e:
            logger.error("TOKEN_VERIFICATION_ERROR", error=str(e))
            raise ValueError(f"Unexpected error verifying token: {str(e)}")

    def get_user_from_token(self, token: str) -> Dict:
        """
        Extract user information from verified token.

        Args:
            token: JWT token string

        Returns:
            dict: User information including:
                - user_id: Auth0 user ID (sub claim)
                - email: User email
                - roles: List of role names from custom claim

        Raises:
            ValueError: If token is invalid
        """
        payload = self.verify_token(token)

        # Extract user info
        user_info = {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get(ROLES_CLAIM_NAMESPACE, []),
        }

        # Validate required fields
        if not user_info["user_id"]:
            raise ValueError("Token missing 'sub' claim (user ID)")

        return user_info

    def verify_superadmin(self, token: str) -> Dict:
        """
        Verify token and check for superadmin role.

        Args:
            token: JWT token string

        Returns:
            dict: User information if user is superadmin

        Raises:
            ValueError: If token invalid or user not superadmin
        """
        user = self.get_user_from_token(token)

        # Check for superadmin role
        if "FI-superadmin" not in user["roles"]:
            logger.warning(
                "SUPERADMIN_ACCESS_DENIED",
                user_id=user["user_id"],
                roles=user["roles"],
            )
            raise ValueError("User does not have superadmin role")

        logger.info(
            "SUPERADMIN_ACCESS_GRANTED",
            user_id=user["user_id"],
            email=user.get("email"),
        )

        return user


# Singleton instance
_verifier: Optional[Auth0JWTVerifier] = None


def get_jwt_verifier() -> Auth0JWTVerifier:
    """Get singleton JWT verifier instance"""
    global _verifier
    if _verifier is None:
        _verifier = Auth0JWTVerifier()
    return _verifier
