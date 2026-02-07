from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from backend.infrastructure.auth.domain.entities.user import UserRole
from backend.infrastructure.auth.services.local_token_service import LocalTokenService


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-that-is-at-least-32-characters-long")


@pytest.fixture()
def token_service():
    return LocalTokenService()


@pytest.mark.asyncio
async def test_create_and_validate_access_token(token_service):
    token = token_service.create_access_token(
        user_id="user-123",
        email="user@example.com",
        roles=[UserRole.SUPERADMIN],
        clinic_id=None,
        name="Test User",
    )

    payload = await token_service.validate(token)

    assert payload.subject == "user-123"
    assert payload.email == "user@example.com"
    assert payload.roles == [UserRole.SUPERADMIN]


@pytest.mark.asyncio
async def test_validate_expired_token(token_service):
    secret = os.environ["JWT_SECRET"]
    now = datetime.now(UTC)

    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "user@example.com",
            "roles": [UserRole.SUPERADMIN.value],
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=1),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        await token_service.validate(token)


@pytest.mark.asyncio
async def test_validate_bad_signature():
    svc = LocalTokenService()
    token = jwt.encode(
        {
            "sub": "user-123",
            "email": "user@example.com",
            "roles": [],
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "wrong-secret-key-that-is-also-32-chars",
        algorithm="HS256",
    )

    with pytest.raises(ValueError):
        await svc.validate(token)


def test_create_refresh_token(token_service):
    raw, hashed, expires_at = token_service.create_refresh_token()

    assert raw != hashed
    assert len(raw) == 64  # hex-encoded 32 bytes
    assert token_service.hash_token(raw) == hashed
    assert expires_at > datetime.now(UTC)


def test_hash_token_deterministic(token_service):
    raw = "test-token-value"
    h1 = token_service.hash_token(raw)
    h2 = token_service.hash_token(raw)
    assert h1 == h2
