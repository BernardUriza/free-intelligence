from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
import jwt
import structlog

from ...domain import ITokenService, TokenPayload

logger = structlog.get_logger(__name__)


class JWKSFetcher:
    """
    Fetches and caches JWKS (JSON Web Key Set) from Auth0.

    Features:
    - TTL-based caching (default 5 minutes)
    - Automatic retry with exponential backoff (3 attempts)
    - Graceful degradation: uses stale cache if fetch fails
    - Thread-safe via asyncio lock
    """

    def __init__(
        self,
        jwks_url: str,
        ttl_seconds: int = 300,
        client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
    ):
        self.jwks_url = jwks_url
        self.ttl_seconds = ttl_seconds
        self.max_retries = max_retries
        self._client = client or httpx.AsyncClient()
        self._jwks: dict[str, Any] | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_jwk(self, kid: str) -> dict[str, Any]:
        if not kid:
            raise ValueError("JWT header missing kid")

        async with self._lock:
            await self._ensure_jwks()
            jwk = self._find_key(kid)
            if jwk:
                return jwk

            # Refresh once if not found (key rotation scenario)
            self._jwks = None
            await self._ensure_jwks()
            jwk = self._find_key(kid)
            if jwk:
                return jwk

        raise ValueError(f"Signing key not found for kid={kid}")

    async def _fetch_with_retry(self) -> dict[str, Any]:
        """Fetch JWKS with exponential backoff retry."""
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.get(self.jwks_url, timeout=5.0)
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2**attempt
                    logger.warning(
                        "jwks_fetch_retry",
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        wait_seconds=wait_time,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait_time)

        # All retries failed
        raise last_error or Exception("JWKS fetch failed after retries")

    async def _ensure_jwks(self) -> None:
        now = time.time()
        if self._jwks and now < self._expires_at:
            return

        try:
            self._jwks = await self._fetch_with_retry()
            self._expires_at = now + self.ttl_seconds
            logger.debug("jwks_refreshed", jwks_url=self.jwks_url)
        except Exception as exc:
            # Graceful degradation: if we have stale cache, extend TTL and use it
            if self._jwks:
                self._expires_at = now + 60  # Extend by 1 minute
                logger.warning(
                    "jwks_using_stale_cache",
                    extended_ttl_seconds=60,
                    error=str(exc),
                )
            else:
                # No cache available, must fail
                logger.error("jwks_fetch_failed", error=str(exc))
                raise

    def _find_key(self, kid: str) -> dict[str, Any] | None:
        if not self._jwks:
            return None
        for key in self._jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        return None


class JWTValidator(ITokenService):
    def __init__(
        self,
        issuer: str,
        audience: str,
        algorithms: list[str],
        roles_claim_key: str,
        jwks_fetcher: JWKSFetcher,
        leeway_seconds: int = 30,
    ):
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms
        self.roles_claim_key = roles_claim_key
        self.jwks_fetcher = jwks_fetcher
        self.leeway_seconds = leeway_seconds

    async def validate(self, token: str) -> TokenPayload:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            jwk = await self.jwks_fetcher.get_jwk(kid)
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

            claims = jwt.decode(
                token,
                signing_key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
            )

            return TokenPayload.from_claims(claims, roles_claim_key=self.roles_claim_key)

        except jwt.ExpiredSignatureError as exc:  # type: ignore[attr-defined]
            logger.warning("jwt_expired", error=str(exc))
            raise ValueError("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            logger.warning("jwt_invalid", error=str(exc))
            raise ValueError(f"Invalid token: {exc}") from exc
        except Exception as exc:  # pragma: no cover - safety net
            logger.error("jwt_validation_error", error=str(exc))
            raise ValueError(f"Unexpected token validation error: {exc}") from exc
