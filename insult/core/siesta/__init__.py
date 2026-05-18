"""Siesta — auto-pause coordination between consolidator and bot.

While the memory consolidator runs (a separate Azure Container App Job),
the bot replica goes silent: it stores incoming messages, reacts with
🛌 to acknowledge them, but does not call the LLM. This avoids races
on the data plane and saves tokens on responses generated against state
that's about to be replaced.

Public API:
- :class:`SiestaSnapshot`, :class:`SiestaPhase`: in-memory state types.
- :class:`SiestaPoller`: bot-side periodic state reader.
- ``mark_started`` / ``mark_progress`` / ``mark_finished``: consolidator-side writers.

v3.9.46 (POST-DEPLOY-1): coordination moved from `blob_metadata` (Azure
blob metadata fields hijacked on `memory.db` blob) to `pg_state`
(Postgres `siesta_state` table). The blob is no longer the channel.
"""

from insult.core.siesta.coordination.pg_state import (
    mark_finished,
    mark_progress,
    mark_started,
    read_snapshot,
)
from insult.core.siesta.coordination.poller import (
    DEFAULT_INTERVAL_SECONDS,
    SiestaPoller,
)
from insult.core.siesta.state import AWAKE, SiestaPhase, SiestaSnapshot

__all__ = [
    "AWAKE",
    "DEFAULT_INTERVAL_SECONDS",
    "SiestaPhase",
    "SiestaPoller",
    "SiestaSnapshot",
    "mark_finished",
    "mark_progress",
    "mark_started",
    "read_snapshot",
]
