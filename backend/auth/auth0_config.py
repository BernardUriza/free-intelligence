"""
Free Intelligence - Auth0 Configuration
HIPAA Card: G-003 - JWT + RBAC middleware FastAPI (Auth0 Integration)
Author: Bernard Uriza Orozco
Created: 2025-11-17

Auth0 OAuth2/OIDC configuration for production-grade authentication.
"""
from __future__ import annotations

import os

# ============================================================================
# Auth0 Configuration
# ============================================================================

# Auth0 Domain (from dashboard) - Note: include region subdomain (.us.auth0.com)
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "dev-1r4daup7ofj7q6gn.us.auth0.com")

# Auth0 Client ID (from application settings)
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp")

# Auth0 Client Secret (keep in environment variables, not in code!)
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")

# API Identifier (Audience) - this is your API's unique identifier in Auth0
# You need to create an API in Auth0 Dashboard → Applications → APIs
AUTH0_API_IDENTIFIER = os.getenv("AUTH0_API_IDENTIFIER", "https://api.fi-aurity.duckdns.org")

# Auth0 Algorithms (RS256 is the default for Auth0)
ALGORITHMS = ["RS256"]

# JWKS URL (JSON Web Key Set) - Auth0's public keys for token verification
JWKS_URL = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"

# Token issuer (must match the 'iss' claim in the token)
ISSUER = f"https://{AUTH0_DOMAIN}/"

# Frontend URLs (for CORS and redirects)
FRONTEND_URL_PROD = os.getenv("FRONTEND_URL_PROD", "https://fi-aurity.duckdns.org")
FRONTEND_URL_DEV = os.getenv("FRONTEND_URL_DEV", "http://localhost:9000")


# ============================================================================
# Auth0 Custom Claims (for RBAC)
# ============================================================================

# Auth0 stores custom claims with namespaced keys
# Example: "https://aurity.app/roles": ["MEDICO"]
AUTH0_NAMESPACE = "https://aurity.app/"

# Custom claim keys
ROLES_CLAIM_KEY = f"{AUTH0_NAMESPACE}roles"
USER_METADATA_CLAIM_KEY = f"{AUTH0_NAMESPACE}user_metadata"


# ============================================================================
# Validation
# ============================================================================


def validate_config() -> None:
    """Validate Auth0 configuration on startup."""
    errors = []

    if not AUTH0_DOMAIN:
        errors.append("AUTH0_DOMAIN is not set")

    if not AUTH0_CLIENT_ID:
        errors.append("AUTH0_CLIENT_ID is not set")

    if not AUTH0_API_IDENTIFIER:
        errors.append("AUTH0_API_IDENTIFIER is not set (create API in Auth0 Dashboard)")

    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(
            f"❌ Auth0 configuration errors:\n{error_msg}\n\n"
            "Set these environment variables:\n"
            "  export AUTH0_DOMAIN=dev-1r4daup7ofj7q6gn.us.auth0.com\n"
            "  export AUTH0_CLIENT_ID=rYOowVCxSqeSNFVOFsZuVIiYsjw4wkKp\n"
            "  export AUTH0_API_IDENTIFIER=https://api.fi-aurity.duckdns.org"
        )

    print("✅ Auth0 configuration validated:")
    print(f"   Domain: {AUTH0_DOMAIN}")
    print(f"   Client ID: {AUTH0_CLIENT_ID}")
    print(f"   API Identifier: {AUTH0_API_IDENTIFIER}")
    print(f"   JWKS URL: {JWKS_URL}")
