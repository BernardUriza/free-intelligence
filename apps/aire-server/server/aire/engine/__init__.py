"""AIRE owns the SDK.

This package is the `ClaudeCodeBackend` engine copied from fi-runner — the one
that already owned the Claude Agent SDK: it boots the `ClaudeSDKClient`, runs
the turn loop, drains the typed events — stripped of every fi-runner
dependency, plus the two things that make AIRE what it is:

- **MODES** (`options.py`): `complete` (no tools — the SUBSTITUTE for the raw
  Messages API) and `agent` (tools — the ENHANCER). The SDK is the engine of
  ONE mode, not AIRE's identity.
- **Its own MEMORY**: the Postgres `session_store`, sole owner, injected. The
  Claude API is stateless; AIRE is "the Claude API, but it remembers".

What is NOT done: importing fi-runner. AIRE owns this code — before, AIRE
*imported* the engine and depended on a repo another agent was editing.

The spine (thirty-line law): `core` is the Engine facade, `contract` the typed
results, `options` the modes dial + SDK options factory, `pool` the hot client
cache, `drain` the turn-loop event drainer, `turn` one turn's lifecycle.

Around it, one concept per file rather than an enumeration that goes stale the
next time one is added: the credential rotor, the spend ledger, the cage,
fire-and-forget turns, vision, the tool registry and its tenants, the guards.
"""

from .contract import BudgetExceeded, SlotBusy, ToolCall, TurnResult, TurnSpec
from .core import Engine
from .options import DEFAULT_MODE, MODES, SYSTEM_PROMPT

__all__ = ["BudgetExceeded", "DEFAULT_MODE", "Engine", "MODES",
           "SYSTEM_PROMPT", "SlotBusy", "ToolCall", "TurnResult", "TurnSpec"]
