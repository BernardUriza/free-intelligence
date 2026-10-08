"""Last-seen credential failure — the honest half of /health.

A dead upstream credential is the one failure every proxy shows green for: the
2026-08-03 outage had the personas answering "…" for THREE DAYS (token revoked
2026-07-20 by an unrelated `claude setup-token` in another repo) while
`/health`, the CD smoke and the logs all looked fine. See
`engineering-playbook/rules/claude-max-oauth-single-token.md`.

On the AIRE route the credential lives on the droplet and a dead one surfaces
as the door's structured `credentials_exhausted` code — `aire_route` calls
``mark_failure`` there and ``clear_failure`` on every successful turn, so
/health's `credentials_rejected` reflects a REAL turn's verdict, never a probe
that cannot fail. (The SDK-prose sniffer that used to live here died with the
local SDK host — AIRE reports the failure as data, not as a persona-shaped
sentence.)
"""

from __future__ import annotations

import time
from typing import Any

_last_failure: dict[str, Any] | None = None


def mark_failure(text: str) -> None:
    global _last_failure
    _last_failure = {"at": time.time(), "detail": text[:200]}


def clear_failure() -> None:
    global _last_failure
    _last_failure = None


def last_failure() -> dict[str, Any] | None:
    return _last_failure
