"""Pure data types for the siesta system.

The siesta is the bot's "I'm asleep, the consolidator is running" state.
Cross-process coordination (consolidator job ↔ bot replica) flows through
Azure blob metadata; everything in this module is the in-memory shape of
that state once the bot has read it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class SiestaPhase(str, Enum):
    """Coarse-grained phases the consolidator advances through.

    Maps to neuroscience-inspired sleep stages used by similar systems
    (OpenClaw Dreaming, Claude Code AutoDream). LIGHT is fact ingestion +
    judge call, DEEP is when the apply_plan transaction is running, REM
    is the post-apply hard-purge + diary generation. AWAKE is the absent
    state — no consolidation in flight.
    """

    AWAKE = "awake"
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"


@dataclass(frozen=True)
class SiestaSnapshot:
    """The bot's view of the consolidator's state at a point in time.

    Built from blob metadata. Frozen because it's a value type — every
    poll produces a new snapshot, never a mutation.
    """

    phase: SiestaPhase
    started_at: datetime | None = None
    total_users: int = 0
    processed_users: int = 0
    current_user_id: str | None = None

    @property
    def is_active(self) -> bool:
        """Whether the consolidator is doing work right now."""
        return self.phase != SiestaPhase.AWAKE

    @property
    def progress_pct(self) -> int:
        """Whole-number percent of users processed. 0 when total unknown."""
        if self.total_users <= 0:
            return 0
        return min(100, int(100 * self.processed_users / self.total_users))

    @property
    def elapsed_seconds(self) -> int:
        """Seconds since the run started. 0 when not started."""
        if self.started_at is None:
            return 0
        return max(0, int((datetime.now(UTC) - self.started_at).total_seconds()))


AWAKE = SiestaSnapshot(phase=SiestaPhase.AWAKE)
"""Singleton for the inactive state — saves an allocation on every poll."""
