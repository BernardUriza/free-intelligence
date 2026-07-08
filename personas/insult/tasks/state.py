"""Shared mutable state for proactive-messaging coordination.

Every loop that messages a channel unprompted consults ``last_proactive_ts``
+ ``unanswered`` through ``should_send_now`` so two loops never double-tap
the same channel. The proactive task owns the writes; other consumers only
read. This dataclass lives here so consumers in separate modules share a
single instance.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

log = structlog.get_logger()


@dataclass
class ProactiveState:
    """One instance, shared by every unprompted-messaging loop."""

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
