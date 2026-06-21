"""fi-runner auth primitive — Auth0 RS256/JWKS validation + the FastAPI gate.

Offline: a throwaway RS256 keypair signs tokens and the JWKS lookup is mocked, so
no Auth0 tenant or network is touched (mirrors the store-fixture pattern).
"""

from __future__ import annotations

import datetime as _dt

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from fi_runner.auth import (
    AuthConfig,
    AuthError,
    Auth0Validator,
    Principal,
    make_auth_dependency,
)

DOMAIN = "dev-test.us.auth0.com"
AUDIENCE = "https://api.og118.ai"
ISSUER = f"https://{DOMAIN}/"


@pytest.fixture(scope="module")
def keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return key.public_key(), priv


def _mint(priv, *, aud=AUDIENCE, iss=ISSUER, sub="auth0|abc", ttl=3600, **extra) -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss,
        "iat": now - _dt.timedelta(seconds=10),
        "exp": now + _dt.timedelta(seconds=ttl),  # ttl<0 → already expired
        **extra,
    }
    return jwt.encode(payload, priv, algorithm="RS256")


@pytest.fixture
def validator(keypair, monkeypatch):
    pub, _ = keypair
    v = Auth0Validator(AuthConfig(domain=DOMAIN, audience=AUDIENCE))

    class _Key:
        key = pub

    # Mock the JWKS network lookup — return our test public key for any token.
    monkeypatch.setattr(v._jwks, "get_signing_key_from_jwt", lambda token: _Key())
    return v


def test_validate_good_token_returns_principal(validator, keypair) -> None:
    _, priv = keypair
    token = _mint(priv, sub="auth0|mom", email="mama@papeleria.mx")
    p = validator.validate(token)
    assert isinstance(p, Principal)
    assert p.sub == "auth0|mom"
    assert p.email == "mama@papeleria.mx"
    assert not p.is_legacy_bearer


def test_validate_expired_raises(validator, keypair) -> None:
    _, priv = keypair
    with pytest.raises(AuthError):
        validator.validate(_mint(priv, ttl=-3600))


def test_validate_wrong_audience_raises(validator, keypair) -> None:
    _, priv = keypair
    with pytest.raises(AuthError):
        validator.validate(_mint(priv, aud="https://someone-elses-api"))


def test_validate_wrong_issuer_raises(validator, keypair) -> None:
    _, priv = keypair
    with pytest.raises(AuthError):
        validator.validate(_mint(priv, iss="https://evil.example/"))


def test_validate_garbage_raises(validator) -> None:
    with pytest.raises(AuthError):
        validator.validate("not-a-jwt")


# --- The FastAPI dependency (dual-accept + 401) ---

def _client(dep):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/whoami")
    def whoami(principal: Principal = Depends(dep)) -> dict:  # noqa: B008
        return {"sub": principal.sub, "legacy": principal.is_legacy_bearer}

    return TestClient(app)


def test_dependency_accepts_auth0_jwt(validator, keypair) -> None:
    _, priv = keypair
    client = _client(make_auth_dependency(validator))
    r = client.get("/whoami", headers={"Authorization": f"Bearer {_mint(priv, sub='auth0|x')}"})
    assert r.status_code == 200
    assert r.json() == {"sub": "auth0|x", "legacy": False}


def test_dependency_dual_accepts_legacy_bearer(validator) -> None:
    client = _client(make_auth_dependency(validator, legacy_bearer="s3cr3t"))
    r = client.get("/whoami", headers={"Authorization": "Bearer s3cr3t"})
    assert r.status_code == 200
    assert r.json() == {"sub": "legacy-bearer", "legacy": True}


def test_dependency_auth0_only_rejects_bearer(validator) -> None:
    client = _client(make_auth_dependency(validator))  # no legacy_bearer
    r = client.get("/whoami", headers={"Authorization": "Bearer s3cr3t"})
    assert r.status_code == 401


def test_dependency_missing_header_401(validator) -> None:
    client = _client(make_auth_dependency(validator, legacy_bearer="s3cr3t"))
    assert client.get("/whoami").status_code == 401
