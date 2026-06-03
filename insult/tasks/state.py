"""Shared mutable state for proactive-messaging coordination.

Proactive check-ins and the Moltbook inbound digest must NOT double-tap the
same channel, so both consult ``last_proactive_ts`` + ``unanswered`` through
``should_send_now``. The proactive task owns the writes; inbound only reads.
This dataclass lives here so both tasks — now in separate modules — share a
single instance.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

log = structlog.get_logger()


@dataclass
class ProactiveState:
    """One instance, shared by the proactive + inbound loops."""

    last_proactive_ts: float | None = None
    unanswered: int = 0  # exponential-backoff counter, bumped per unanswered proactive

    def reset(self) -> None:
        """Reset the unanswered counter when a user replies after a proactive.

        Exposed on the bot as ``_reset_proactive_backoff`` so ChatCog's batch
        manager can call it on the next inbound user message.
        """
        if self.unanswered > 0:
            log.info("proactive_backoff_reset", was=self.unanswered)
            self.unanswered = 0
