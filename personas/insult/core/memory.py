"""Legacy re-export shim — the memory subsystem moved to khimeras_shared.memory (PR-1c).

The longitudinal store is shared infrastructure: the persona_gateway hands ONE
MemoryStore to every sibling persona-bot, so the data plane belongs in the
shared layer, not inside a persona. This shim preserves the historical
``personas.insult.core.memory`` import path for persona-internal callers; the
single source of truth is ``khimeras_shared.memory``.
"""

from khimeras_shared.memory import MemoryStore, build_context, format_relative_time

__all__ = ["MemoryStore", "build_context", "format_relative_time"]
