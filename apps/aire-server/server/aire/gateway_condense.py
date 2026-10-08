"""A relayed request, split into what is NEW and what the log already holds (#41).

The Messages API is stateless, so a conversational client re-sends everything on
every call: turns 1..N−1, the whole `system` array, and every tool's full JSON
schema. The mirror stored all of it, beside the rows that already held the same
bytes — measured on 15 live days, `aire_gateway_log`'s request rows were **63.7
MB against 8 MB of responses**.

Two different redundancies, and the measurement is what separated them:

- **`messages`** — only the last one is kept. The rest are the earlier rows of
  the same `session_id`; reading them in order IS the conversation, which is
  what an append-only log is for. The front already agrees — every gateway view
  pulls `$.messages[last]`, and its own comment calls the rest "history the
  caller resent".
- **`system` and `tools`** — these are not history, they are the same handful of
  values sent over and over. Across all 585 request rows there are **33 distinct
  system arrays and 9 distinct tool sets**. So they are content-addressed: the
  value is stored ONCE in `aire_gateway_blob` under its fingerprint, and the row
  keeps the fingerprint. Replaying every real row through this: 63.7 MB → 30.8
  MB, a 2.1x cut with nothing lost — a fingerprint is a JOIN, not a search.
  Keying them per-session instead was measured too, and gives only 1.5x.

This module is pure: it decides, it does not write. `gateway_mirror` performs
the I/O and, if a blob write ever fails, stores the value inline — degrading to
the old fat-but-correct row rather than losing it.

What this does NOT do: truncate. A single huge message is not redundancy — the
largest request measured carried ONE turn of 1,597 KB, and those bytes exist
nowhere else. Cutting them would be loss, and the log records what arrived
([[log-is-the-truth]]).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

REF = "$ref"          # marks a field whose value lives in aire_gateway_blob
ELIDED = "$elided"    # what this row does not repeat, and where to find it
DEDUPED = ("system", "tools")


def fingerprint(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def split(body: Any) -> tuple[Any, dict[str, Any]]:
    """`(the row to append, {fingerprint: value} to store once)`.

    A non-dict body passes through untouched with nothing to store: the mirror
    must never be the reason a relay's memory is lost."""
    if not isinstance(body, dict):
        return body, {}
    row = {k: v for k, v in body.items() if k not in ("messages", *DEDUPED)}
    elided: dict[str, Any] = {}
    blobs: dict[str, Any] = {}
    messages = body.get("messages")
    if isinstance(messages, list):
        row["messages"] = messages[-1:]
        if len(messages) > 1:
            elided["messages"] = len(messages) - 1
    for field in DEDUPED:
        if field not in body:
            continue
        digest = fingerprint(body[field])
        blobs[digest] = body[field]
        elided[field] = {REF: digest}
    if elided:
        row[ELIDED] = elided
    return row, blobs


def inline(row: Any, blobs: dict[str, Any], body: Any) -> Any:
    """The fallback when a blob could not be stored: put those values back in the
    row. A fatter row is right; a reference to something that was never written
    is a dangling pointer, and this log is read by a front that cannot fix it."""
    if not isinstance(row, dict) or not isinstance(body, dict):
        return row
    restored = dict(row)
    elided = dict(restored.get(ELIDED) or {})
    for field in DEDUPED:
        if field in body and fingerprint(body[field]) in blobs:
            restored[field] = body[field]
            elided.pop(field, None)
    if elided:
        restored[ELIDED] = elided
    else:
        restored.pop(ELIDED, None)
    return restored
