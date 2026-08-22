"""The Bearer check, in one place, because two services now stand behind it.

`server.py` gates the LLM door with it; `nickname.py` (backlog #32) gates the
landing's generator with the same secrets. The check is five lines, which is
exactly why it must not be copied: a constant-time comparison that gets fixed in
one service and not the other is a hole nobody sees. It was copied once already
— the 2026-08-07 bug where a non-ASCII token raised `TypeError` and answered 500
instead of 401 lives on in the comment below, and it must never be re-learned in
a second module.

This module imports nothing heavy on purpose. The nickname service must be able
to check a token without dragging the engine (and its memory) into its process.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Request

# One slot per CONSUMER, not one shared secret: a credential is scoped to the
# surface it was handed to, so a leak is revoked by emptying ONE variable and no
# sibling consumer is disturbed. AIRE_AUTH_TOKEN is Bernard's own, CANARY the
# Azure front's, RUNNER discord-bot's persona-runner (stage 2).
ACCEPTED_TOKENS = tuple(
    t for t in (os.environ.get("AIRE_AUTH_TOKEN", ""),
                os.environ.get("AIRE_CANARY_TOKEN", ""),
                os.environ.get("AIRE_RUNNER_TOKEN", "")) if t
)


def presented_token(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def accepted(presented: str) -> bool:
    # Compared as BYTES: compare_digest on str raises TypeError on non-ASCII
    # input (seen live 2026-08-07 — a garbled Bearer token 500ed instead of 401).
    ok = False
    for token in ACCEPTED_TOKENS:  # check every token — no short-circuit timing leak
        ok |= hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8"))
    return ok
