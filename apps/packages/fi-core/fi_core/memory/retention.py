"""Retention policies for soft-deleted facts.

A ``MemoryStore`` distinguishes soft-delete (mark ``deleted_at``,
remain queryable through an explicit "include deleted" call) from
hard-purge (DELETE row permanently). The retention window is the
gap: how long does a soft-deleted row remain recoverable before
permanent removal.

Discord-bot's production setup uses 90 days, encoded as
``SOFT_DELETE_RETENTION_SECONDS = 90 * 86400`` in
``insult/core/memory_consolidator.py``. That number was tuned by
operations: long enough that a misclassified DELETE is almost always
caught by the next consolidation pass plus operator review, short
enough that the table doesn't accumulate forever.

The :class:`RetentionPolicy` Protocol abstracts the window so
consumers can plug in dynamic policies (e.g. tier-based — keep VIP
users' deletions for 180d, normal for 30d) without forking the store.
``Default90d`` ships the discord-bot constant as the out-of-box default.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class RetentionPolicy(Protocol):
    """Returns the cutoff timestamp before which soft-deleted rows can be purged.

    A retention policy may use ``principal_id`` and ``category`` to make
    per-tenant or per-category decisions; the simplest impls ignore
    both. Returns a unix-seconds float; rows with ``deleted_at < cutoff``
    are eligible for hard-purge.
    """

    def cutoff(
        self,
        *,
        now: float | None = None,
        principal_id: str | None = None,
        category: str | None = None,
    ) -> float:
        """Return the unix-seconds threshold for hard-purge eligibility."""
        ...


@dataclass(frozen=True, slots=True)
class Default90d:
    """Fixed-window 90-day retention policy.

    Discord-bot's production-validated default. The window is the same
    for every principal and category — simple, predictable, audited.
    """

    seconds: int = 90 * 86_400  # 90 days

    def cutoff(
        self,
        *,
        now: float | None = None,
        principal_id: str | None = None,  # noqa: ARG002 - intentional in Protocol
        category: str | None = None,  # noqa: ARG002 - intentional in Protocol
    ) -> float:
        """``now - self.seconds``. Defaults ``now`` to ``time.time()``."""
        base = now if now is not None else time.time()
        return base - self.seconds


@dataclass(frozen=True, slots=True)
class FixedWindow:
    """Generic fixed-window retention with a caller-controlled duration.

    Use this when 90 days is wrong for your domain (e.g. medical
    records may need 7+ years, ephemeral chat may want 7 days).
    """

    seconds: int

    def cutoff(
        self,
        *,
        now: float | None = None,
        principal_id: str | None = None,  # noqa: ARG002 - intentional in Protocol
        category: str | None = None,  # noqa: ARG002 - intentional in Protocol
    ) -> float:
        base = now if now is not None else time.time()
        return base - self.seconds


@dataclass(frozen=True, slots=True)
class NeverPurge:
    """Retention policy that never purges anything.

    Use for audit-grade stores where soft-delete is the terminal state
    and rows must remain accessible for compliance review indefinitely.
    """

    def cutoff(
        self,
        *,
        now: float | None = None,  # noqa: ARG002 - intentional in Protocol
        principal_id: str | None = None,  # noqa: ARG002 - intentional in Protocol
        category: str | None = None,  # noqa: ARG002 - intentional in Protocol
    ) -> float:
        """Returns ``-inf`` so no row ever satisfies ``deleted_at < cutoff``."""
        return float("-inf")
