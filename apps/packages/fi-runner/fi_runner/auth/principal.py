"""The authenticated identity a consumer gets back from the auth layer.

Framework-thin on purpose: just the verified identity (the Auth0 subject = the
consumer's account_id, plus email and the raw claims). RBAC / DB users are a
consumer concern (cf. AURITY's richer ``User``); the framework stays minimal so
every consumer can map ``Principal`` onto its own account model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Principal:
    """A verified caller. ``sub`` is the stable account id (Auth0 ``sub`` claim)."""

    sub: str
    email: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)

    @property
    def is_legacy_bearer(self) -> bool:
        """True for the synthetic principal minted when a caller authenticates
        with the legacy shared bearer during a dual-mode transition."""
        return bool(self.claims.get("legacy"))


LEGACY_BEARER_SUB = "legacy-bearer"


def legacy_principal() -> Principal:
    """The synthetic identity for a legacy-bearer caller (dual-mode transition)."""
    return Principal(sub=LEGACY_BEARER_SUB, email=None, claims={"legacy": True})
