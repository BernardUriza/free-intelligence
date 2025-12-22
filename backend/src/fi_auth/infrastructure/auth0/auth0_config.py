from __future__ import annotations

from dataclasses import dataclass

import os


@dataclass
class Auth0Config:
    domain: str
    audience: str
    algorithms: list[str]
    roles_claim_key: str

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}/"

    @property
    def jwks_url(self) -> str:
        return f"https://{self.domain}/.well-known/jwks.json"


def load_auth0_config() -> Auth0Config:
    domain = os.getenv("AUTH0_DOMAIN", "dev-1r4daup7ofj7q6gn.us.auth0.com")
    audience = os.getenv("AUTH0_API_IDENTIFIER", "https://app.aurity.io")
    roles_claim_key = os.getenv("AUTH0_ROLES_CLAIM", "https://aurity.app/roles")

    if not domain:
        raise ValueError("AUTH0_DOMAIN is required for Auth0 auth provider")
    if not audience:
        raise ValueError("AUTH0_API_IDENTIFIER is required for Auth0 auth provider")

    return Auth0Config(
        domain=domain,
        audience=audience,
        algorithms=["RS256"],
        roles_claim_key=roles_claim_key,
    )
