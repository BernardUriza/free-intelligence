from __future__ import annotations

from dataclasses import dataclass

import os


@dataclass
class Auth0Config:
    domain: str
    audience: str
    algorithms: list[str]
    roles_claim_key: str
    management_api_token: str | None = None  # For updating user metadata

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}/"

    @property
    def jwks_url(self) -> str:
        return f"https://{self.domain}/.well-known/jwks.json"


def load_auth0_config() -> Auth0Config:
    """
    Load Auth0 configuration from environment variables.

    IMPORTANT: No hardcoded production defaults. Each environment
    must explicitly set these values to prevent dev/prod confusion.
    """
    domain = os.getenv("AUTH0_DOMAIN")
    audience = os.getenv("AUTH0_API_IDENTIFIER")
    roles_claim_key = os.getenv("AUTH0_ROLES_CLAIM", "https://aurity.app/roles")
    management_api_token = os.getenv("AUTH0_MANAGEMENT_API_TOKEN")  # Optional

    if not domain:
        raise ValueError("AUTH0_DOMAIN is required for Auth0 auth provider")
    if not audience:
        raise ValueError("AUTH0_API_IDENTIFIER is required for Auth0 auth provider")

    return Auth0Config(
        domain=domain,
        audience=audience,
        algorithms=["RS256"],
        roles_claim_key=roles_claim_key,
        management_api_token=management_api_token,
    )
