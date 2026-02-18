"""Local JWT token service using HS256.

Implements ITokenService for self-hosted auth.
Access tokens are short-lived (15min), refresh tokens are DB-backed (7d).
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import jwt
import structlog

from ..domain.entities.token import TokenPayload
from ..domain.entities.user import UserRole
from ..domain.interfaces.token_service import ITokenService

logger = structlog.get_logger(__name__)

# Defaults (overridable via env)
_DEFAULT_ACCESS_TTL = 900  # 15 minutes
_DEFAULT_REFRESH_TTL = 604800  # 7 days


class LocalTokenService(ITokenService):
    """HS256 JWT token service for local authentication."""

    def __init__(self, secret: str | None = None) -> None:
        self.secret = secret or os.getenv("JWT_SECRET", "")
        if not self.secret or len(self.secret) < 32:
            raise ValueError(
                "JWT_SECRET must be set and at least 32 characters long. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        self.algorithm = "HS256"
        self.access_ttl = int(os.getenv("ACCESS_TOKEN_TTL", str(_DEFAULT_ACCESS_TTL)))
        self.refresh_ttl = int(os.getenv("REFRESH_TOKEN_TTL", str(_DEFAULT_REFRESH_TTL)))

    def create_access_token(
        self,
        user_id: str,
        email: str,
        roles: list[UserRole],
        clinic_id: str | None = None,
        name: str | None = None,
    ) -> str:
        """Create a short-lived access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "roles": [r.value for r in roles],
            "iss": "aurity-local",
            "iat": now,
            "exp": now + timedelta(seconds=self.access_ttl),
            "jti": str(uuid4()),
        }
        if clinic_id:
            payload["clinic_id"] = clinic_id
        if name:
            payload["name"] = name
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self) -> tuple[str, str, datetime]:
        """Create a refresh token.

        Returns:
            (raw_token, token_hash, expires_at)
            The raw token is sent to the client; the hash is stored in DB.
        """
        raw = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.refresh_ttl)
        return raw, token_hash, expires_at

    @staticmethod
    def hash_token(raw: str) -> str:
        """Hash a raw refresh token for DB lookup."""
        return hashlib.sha256(raw.encode()).hexdigest()

    async def validate(self, token: str) -> TokenPayload:
        """Validate an access token and return its payload."""
        try:
            decoded = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                issuer="aurity-local",
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}") from exc

        raw_roles = decoded.get("roles", [])
        parsed_roles: list[UserRole] = []
        for r in raw_roles:
            role = UserRole.coerce(r)
            if role:
                parsed_roles.append(role)

        return TokenPayload(
            subject=decoded["sub"],
            email=decoded.get("email"),
            roles=parsed_roles,
            issuer=decoded.get("iss"),
            tenant_id=decoded.get("tenant_id"),
            expires_at=datetime.fromtimestamp(decoded["exp"], tz=timezone.utc) if "exp" in decoded else None,
            issued_at=datetime.fromtimestamp(decoded["iat"], tz=timezone.utc) if "iat" in decoded else None,
            claims=decoded,
        )
