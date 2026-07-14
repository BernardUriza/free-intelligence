"""Bearer auth for every runner endpoint — fail-closed by construction."""

from __future__ import annotations

import hmac

from fastapi import HTTPException

from persona_runner.core import config


def check_auth(authorization: str | None) -> None:
    """Bearer auth check. Fail-closed when the token is unconfigured (503).

    Timing-safe compare: a 401 must not leak the token prefix through response
    latency. An unconfigured runner refuses EVERY request rather than serving
    the SDK (and its OAuth Max credentials) to anyone who finds the FQDN.
    """
    if not config.RUNNER_AUTH_TOKEN:
        raise HTTPException(503, "Runner auth token not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    provided = authorization[len("Bearer ") :]
    if not hmac.compare_digest(provided, config.RUNNER_AUTH_TOKEN):
        raise HTTPException(401, "Invalid token")
