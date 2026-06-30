"""Auth0 (RS256 / JWKS) access-token validation.

Verifies a bearer JWT against the tenant's published public keys — no shared
secret on the server (RS256 = the server only needs the public JWKS). Key fetch
+ caching is delegated to PyJWT's ``PyJWKClient`` (the maintained primitive — we
don't hand-roll JWKS caching).
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient

from .principal import Principal


class AuthError(Exception):
    """A token failed validation (absent/expired/wrong-audience/wrong-issuer/
    bad-signature). The message is secret-free and safe to surface."""


@dataclass(frozen=True)
class AuthConfig:
    domain: str
    audience: str
    algorithms: tuple[str, ...] = ("RS256",)

    @property
    def issuer(self) -> str:
        return f"https://{self.domain}/"

    @property
    def jwks_url(self) -> str:
        return f"https://{self.domain}/.well-known/jwks.json"


class Auth0Validator:
    """Validates Auth0 access tokens for one tenant + audience. Construct once
    and reuse — the JWKS cache lives on the ``PyJWKClient``."""

    def __init__(self, config: AuthConfig) -> None:
        self.config = config
        self._jwks = PyJWKClient(config.jwks_url)

    def validate(self, token: str) -> Principal:
        """Return the verified :class:`Principal`, or raise :class:`AuthError`."""
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self.config.algorithms),
                audience=self.config.audience,
                issuer=self.config.issuer,
            )
        except jwt.PyJWTError as exc:
            # type-only message: no token bytes, no key material.
            raise AuthError(f"invalid token: {type(exc).__name__}") from None
        except Exception as exc:  # JWKS fetch / key errors
            raise AuthError(f"token verification failed: {type(exc).__name__}") from None
        sub = claims.get("sub")
        if not sub:
            raise AuthError("invalid token: missing sub")
        return Principal(sub=sub, email=claims.get("email"), claims=claims)
