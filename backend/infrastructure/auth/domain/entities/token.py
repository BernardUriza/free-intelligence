from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .user import UserRole


@dataclass
class TokenPayload:
    subject: str
    email: str | None = None
    roles: list[UserRole] = field(default_factory=list)
    issuer: str | None = None
    audience: str | None = None
    tenant_id: str | None = None
    expires_at: datetime | None = None
    issued_at: datetime | None = None
    claims: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_claims(cls, claims: dict[str, Any], roles_claim_key: str) -> TokenPayload:
        raw_roles = claims.get(roles_claim_key) or claims.get("roles") or []
        if isinstance(raw_roles, str):
            raw_roles_list = [raw_roles]
        elif isinstance(raw_roles, list):
            raw_roles_list = raw_roles
        else:
            raw_roles_list = []

        parsed_roles: list[UserRole] = []
        for value in raw_roles_list:
            role = UserRole.coerce(value)
            if role and role not in parsed_roles:
                parsed_roles.append(role)

        expires_at = _parse_timestamp(claims.get("exp"))
        issued_at = _parse_timestamp(claims.get("iat"))

        return cls(
            subject=str(claims.get("sub")),
            email=claims.get("email"),
            roles=parsed_roles,
            issuer=claims.get("iss"),
            audience=claims.get("aud") if isinstance(claims.get("aud"), str) else None,
            tenant_id=claims.get("tenant_id") or claims.get("org_id"),
            expires_at=expires_at,
            issued_at=issued_at,
            claims=claims,
        )


@dataclass
class RefreshToken:
    token: str
    expires_at: datetime | None = None


def _parse_timestamp(value: Any) -> datetime | None:
    try:
        if value is None:
            return None
        return datetime.fromtimestamp(float(value), tz=UTC)
    except Exception:
        return None
