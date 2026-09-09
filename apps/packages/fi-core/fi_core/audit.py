"""fi_core.audit — the two primitives every consumer that records a verdict
about a real person ends up writing, promoted so the second one does not
rewrite them slightly wrong.

Zero-dep, stdlib only, no logger imposed: the consumer decides where the
payload goes (structlog, Log Analytics, an event store) and what is fail-safe
on its own turn path. This module never swallows an error and never reads an
environment variable — both are the consumer's call, because only the
consumer knows what a lost log line costs there.

Provenance: discord-bot #54 (Alex's decisions, 2026-09-07/08) shipped both
shapes in ``khimeras_shared/audit.py`` as the canary; og118 and AIRE run the
same clinical domain and will need exactly these when they log a band.

    from fi_core.audit import audit_period, audited, pseudonym

    code = pseudonym(user_id, key=os.environ.get("CRISIS_AUDIT_KEY"), period=audit_period())
    log.info(**audited("crisis_band_classified", band="HIGH", user_id=code))

Two conditions on the pseudonym are part of the design, not options:

1. **With a secret key, or nothing.** A bare ``sha256(subject)`` over a small,
   enumerable id space (Discord users, patient folios) is reversible by anyone
   holding the member list. ``pseudonym`` returns ``None`` without a key —
   never a keyless hash. ``tests/test_audit.py`` pins this with a test a bare
   sha256 cannot pass: two keys must produce two codes.
2. **The key rotates by period, and the period is visible in the code.**
   ``2026-09:df068944ec77436d`` groups one person's turns inside a month and
   is incomparable across months even when it is the same person — a leaked
   key opens one month, not a life. The period reveals nothing the log's own
   timestamp did not already say.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

#: 64 bits of digest: enough that two subjects of one deployment do not
#: collide, short enough to read in a query. The protection is the key.
DEFAULT_DIGEST_CHARS = 16


def sha256_payload(data: Any) -> str:
    """Stable SHA256 of a JSON-serializable payload (for audit non-repudiation)."""
    encoded = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_period(now: datetime | None = None) -> str:
    """The key-rotation period: the month in UTC, as ``2026-09``.

    An aware ``now`` is converted to UTC first, so a deployment that hands in
    local time at 23:30 on the 30th does not mint next month's code."""
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc)
    return f"{moment.year:04d}-{moment.month:02d}"


def pseudonym(
    subject: str,
    *,
    key: str | None,
    period: str,
    digest_chars: int = DEFAULT_DIGEST_CHARS,
) -> str | None:
    """A code that groups ``subject``'s records within ``period`` without
    identifying them — ``"<period>:<hmac-sha256 prefix>"``, or ``None``.

    ``None`` when there is no subject or no usable key (empty and whitespace
    count as no key: ``KEY=""`` in an app service is the realistic failure,
    not the variable's absence). Never a keyless hash — see the module
    docstring. Byte-compatible with discord-bot's ``pseudonymous_user`` so the
    codes already in its logs stay comparable for the rest of their month."""
    if not subject or not key or not key.strip():
        return None
    digest = hmac.new(key.encode(), f"{period}:{subject}".encode(), hashlib.sha256).hexdigest()
    return f"{period}:{digest[:digest_chars]}"


def audited(event: str, **fields: Any) -> dict[str, Any]:
    """``fields`` plus the event name and an ``audit_hash`` over both.

    The hash covers the name too: without it an ``absent`` row could be
    relabeled as a ``classified`` verdict and still verify. It does not cover
    whatever timestamp the sink stamps on the row — that lives outside the
    payload, so the hash proves the CONTENT did not change, not the hour it
    was archived. Ready to spread into a structlog call:
    ``log.info(**audited("crisis_band_classified", band=...))``."""
    if "audit_hash" in fields:
        raise ValueError("audit_hash is computed here, not passed in")
    payload = {**fields, "event": event}
    return {**payload, "audit_hash": sha256_payload(payload)}
