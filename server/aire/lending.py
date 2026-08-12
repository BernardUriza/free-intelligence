"""The terms on which AIRE lends its own credential (backlog #32, the gateway).

The gateway door is auth-pass-through by default: the caller's credential rides
upstream and AIRE spends nothing. An INVITED key has no Anthropic credential of
its own — that is the whole point of being invited — so for those callers AIRE
substitutes its own, and the invitation's ceiling becomes the only thing between
a stranger and Bernard's account. This module is that boundary.

**The lent credential has its own named slot** — `AIRE_LEND_OAUTH_TOKEN`, or
`AIRE_LEND_API_KEY` when a metered key exists (preferred: it is revocable
without touching the subscription). It deliberately does NOT read the engine's
`CLAUDE_CODE_OAUTH_TOKEN`, even though provisioning fills both from the same file
today — one OAuth token exists per account, so the VALUE is the same. What the
slot buys is that the value is *chosen*: lending can be switched off by clearing
one variable while the engine keeps dispatching, a metered key can replace it
without touching the engine, and no unrelated credential appearing in the
daemon's environment can silently become the thing AIRE hands to strangers. It is
the same reasoning that gave the Azure front its own `AIRE_CANARY_TOKEN` instead
of Bernard's key: the lowest-trust consumer gets its own, revocable alone.

Two headers, never one. An OAuth token is presented as `Authorization: Bearer`
AND requires `anthropic-beta: oauth-2025-04-20` — `/v1/messages` rejects it
without the beta. The caller's own `anthropic-beta` is APPENDED to, never
replaced: the gateway's law is that beta headers forward verbatim, and an
allowlist there breaks clients as they ship new betas.

The concurrency slot lives here for a reason that is not tidiness: the ceiling is
banked when a turn ENDS, so N turns launched together all pass the gate before
any of them pays. Without a slot limit a leaked invitation spends N times its
ceiling by opening N sockets at once.
"""

from __future__ import annotations

import os

OAUTH_BETA = "oauth-2025-04-20"
MAX_INFLIGHT = int(os.environ.get("AIRE_INVITE_CONCURRENCY", "2"))
_inflight: dict[str, int] = {}


def credential() -> tuple[str, str] | None:
    """The header AIRE lends, or None when the slot is empty — which is a real
    configuration, not a failure: no slot means invited keys are told plainly
    that there is nothing to lend, while the engine keeps dispatching."""
    if os.environ.get("AIRE_LEND_API_KEY"):
        return ("x-api-key", os.environ["AIRE_LEND_API_KEY"])
    if os.environ.get("AIRE_LEND_OAUTH_TOKEN"):
        return ("authorization", f"Bearer {os.environ['AIRE_LEND_OAUTH_TOKEN']}")
    return None


def lend(headers: list[tuple[str, str]]) -> list[tuple[str, str]] | None:
    """Swap the caller's credential for AIRE's, keeping every other header the
    gateway would have forwarded. None means AIRE has no credential to lend."""
    lent = credential()
    if lent is None:
        return None
    kept = [(k, v) for k, v in headers if k.lower() not in ("authorization", "x-api-key")]
    if lent[0] == "authorization":
        kept = _with_beta(kept, OAUTH_BETA)
    return [*kept, lent]


def _with_beta(headers: list[tuple[str, str]], flag: str) -> list[tuple[str, str]]:
    """Append a beta flag to whatever the caller already asked for."""
    out, seen = [], False
    for key, value in headers:
        if key.lower() == "anthropic-beta":
            seen = True
            value = value if flag in value else f"{value},{flag}"
        out.append((key, value))
    return out if seen else [*out, ("anthropic-beta", flag)]


def enter(nickname: str) -> bool:
    """Claim one of this key's concurrent turns. False means it is already at
    its limit — the answer is retry, not a bigger bill."""
    running = _inflight.get(nickname, 0)
    if running >= MAX_INFLIGHT:
        return False
    _inflight[nickname] = running + 1
    return True


def leave(nickname: str) -> None:
    running = _inflight.get(nickname, 0) - 1
    if running > 0:
        _inflight[nickname] = running
    else:
        _inflight.pop(nickname, None)
