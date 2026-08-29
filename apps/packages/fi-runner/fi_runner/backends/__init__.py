"""Agent backend implementations.

ONE backend, on purpose. ``ClaudeCodeBackend``, ``CodexBackend`` and the
``SubprocessCLIBackend`` base were deleted on 2026-08-29 when the fleet
consolidated on AIRE: every consumer now enters through the same door.

Why deleting beat keeping them "just in case":

- **They had become a second copy of a runtime AIRE already owns.**
  ``aire-server/server/aire/engine/`` is ``ClaudeCodeBackend`` forked
  deliberately ("What is NOT done: importing fi-runner — AIRE owns this code"),
  so the SDK host lived in two places and only one of them served production.
- **Two ways to run a turn is the parallel-surface smell**, and the unexercised
  one is where the drift accumulates: every fix landed here had to be ported
  there by hand, or silently did not apply.
- **The port stays the port.** :class:`fi_runner.backend.AgentBackend` is still
  a Protocol, so a second backend is a file away if a real second door appears.
  What is gone is the pretence that three of them were maintained.

What went with them, stated plainly rather than discovered later:

- ``PostgresSessionStore`` / ``fi_runner.session_stores`` — the Claude Agent
  SDK's native transcript. AIRE owns memory in its own Postgres, so the runner
  no longer carries a store of its own.
- ``ProviderConfig`` — Codex's API-motor selection. AIRE's door picks the model.
- The only implementation of ``enforces_pinned_args``. The pin contract in
  :attr:`fi_runner.backend.MCPServerSpec.pinned_args` survives ON PURPOSE, and
  :meth:`fi_runner.Runner._pin_args` now REFUSES every pinned turn — because no
  backend can gate a tool argument any more. That refusal is the point: it keeps
  the gap loud until the door implements it, instead of letting a consumer
  believe a tenant is fenced when nothing is fencing it.
"""

from .aire import AIREBackend, AIREDoorError

__all__ = ["AIREBackend", "AIREDoorError"]
