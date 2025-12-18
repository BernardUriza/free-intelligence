from __future__ import annotations

__all__ = [
    "redact_token",
]


def redact_token(token: str | None) -> str:
    if not token:
        return "<redacted>"
    return token[:6] + "…" + token[-4:]
