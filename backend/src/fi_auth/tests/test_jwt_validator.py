from __future__ import annotations

import json
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import UTC, datetime, timedelta

from backend.src.fi_auth.domain.entities.user import UserRole
from backend.src.fi_auth.infrastructure.jwt.jwt_validator import JWTValidator


class StaticJWKSFetcher:
    def __init__(self, jwk: dict):
        self._jwk = jwk

    async def get_jwk(self, kid: str) -> dict:
        return {**self._jwk, "kid": kid}


@pytest.fixture(scope="session")
def rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    return private_key, public_jwk


@pytest.fixture()
def jwt_validator(rsa_keypair):
    private_key, public_jwk = rsa_keypair
    fetcher = StaticJWKSFetcher(public_jwk)
    return private_key, JWTValidator(
        issuer="https://example.auth0.com/",
        audience="https://app.aurity.io",
        algorithms=["RS256"],
        roles_claim_key="https://aurity.app/roles",
        jwks_fetcher=fetcher,
    )


@pytest.mark.asyncio
async def test_validate_token_success(jwt_validator):
    private_key, validator = jwt_validator
    now = datetime.now(UTC)
    kid = "unit-test"

    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "user@example.com",
            "https://aurity.app/roles": [UserRole.SUPERADMIN.value],
            "iss": "https://example.auth0.com/",
            "aud": "https://app.aurity.io",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )

    payload = await validator.validate(token)

    assert payload.subject == "user-123"
    assert payload.email == "user@example.com"
    assert payload.roles == [UserRole.SUPERADMIN]


@pytest.mark.asyncio
async def test_validate_token_expired(jwt_validator):
    private_key, validator = jwt_validator
    expired_at = datetime.now(UTC) - timedelta(minutes=1)
    kid = "unit-test"

    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "user@example.com",
            "https://aurity.app/roles": [UserRole.SUPERADMIN.value],
            "iss": "https://example.auth0.com/",
            "aud": "https://app.aurity.io",
            "iat": expired_at - timedelta(minutes=5),
            "exp": expired_at,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )

    with pytest.raises(ValueError):
        await validator.validate(token)
