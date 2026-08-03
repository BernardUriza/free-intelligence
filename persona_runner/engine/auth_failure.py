"""Credential failure detection — the SDK reports a dead token as PROSE, not an error.

When the OAuth Max token is revoked or expired, the Claude Agent SDK does NOT
raise: it drains a normal-looking stream whose only text is
`"Failed to authenticate. API Error: 401 OAuth access token has been revoked."`,
with `stop_reason="stop_sequence"` and zero tokens on both sides. `/v1/turn`
then treats it as the persona speaking, logs `agent_runner_turn_complete`, and
answers `HTTP 200` — the perfect fake-green. The gateway, seeing a body it
cannot parse into anything useful, degrades to "…", so from Discord the bot is
simply mute, with every proxy (`/health`, the CD smoke, the logs) green.

That is exactly how 2026-08-03 happened: the token was revoked on 2026-07-20 by
an unrelated `claude setup-token` in another repo, and the personas answered
"…" for THREE DAYS with no signal anywhere. See
`engineering-playbook/rules/claude-max-oauth-single-token.md`.

The detector is deliberately multi-signal (see `.claude/rules/robustness.md` on
destructive post-processing): a real turn ALWAYS bills input tokens, so a turn
whose text merely *mentions* a 401 while billing tokens is a persona discussing
HTTP status codes — never a credential failure.
"""

from __future__ import annotations

import re
import time
from typing import Any

_CREDENTIAL_ERROR = re.compile(
    r"(failed to authenticate"
    r"|oauth (?:access )?token (?:has been )?(?:revoked|expired)"
    r"|invalid (?:bearer token|api key|x-api-key)"
    r"|authentication[_ ]error"
    r"|api error: 40[13])",
    re.IGNORECASE,
)

_last_failure: dict[str, Any] | None = None


def looks_like_credential_failure(state: dict[str, Any]) -> bool:
    """True when a drained turn is the SDK reporting dead credentials.

    Requires ALL of: the text matches a credential-error phrase, the turn billed
    NOTHING on either side, and no tool ran. A persona that legitimately writes
    "me salió API Error: 401" bills input tokens and is therefore never caught.
    """
    text = state.get("text") or ""
    if not text or not _CREDENTIAL_ERROR.search(text):
        return False
    if state.get("input_tokens") or state.get("output_tokens"):
        return False
    return not state.get("tool_calls")


def mark_failure(text: str) -> None:
    global _last_failure
    _last_failure = {"at": time.time(), "detail": text[:200]}


def clear_failure() -> None:
    global _last_failure
    _last_failure = None


def last_failure() -> dict[str, Any] | None:
    return _last_failure
