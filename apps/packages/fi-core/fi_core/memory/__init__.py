"""Long-term memory primitives for fi-core.

Sub-modules:
- ``fi_core.memory.types``        — Fact, FactSource, ConsolidationOp dataclasses
- ``fi_core.memory.retention``    — RetentionPolicy Protocol + Default90d impl
- ``fi_core.memory.protocols``    — MemoryStore Protocol
- ``fi_core.memory.stores``       — concrete MemoryStore implementations
- ``fi_core.memory.consolidator`` — FactConsolidator (wraps persona.mcp_server tools)

Design rationale
----------------

``fi_core.memory`` consolidates patterns that already passed the production
filter in two consumers (discord-bot Insult + AURITY medical RAG). It is NOT
new design — it is **extraction**, hardened by months of running traffic on
both deployments.

Why this is a sibling of ``fi_core.stores`` and not a layer above it:

- ``DocumentChunkStore`` (in ``fi_core.rag.protocols``) is a chunk-of-document
  shape. ``MemoryStore`` is a fact-as-atomic-unit shape. They share design
  language (namespace-style isolation, async-first, asyncpg + pgvector for
  the postgres impl) but the primitive is different.
- A fact is closer to a row than a chunk. Forcing it through a chunk-shaped
  Protocol would put a document concept where none belongs.

What this package does NOT ship (and why)
-----------------------------------------

- **Fact extraction LLM calls** — the prompt that turns conversation history
  into "extracted facts" is product-specific. Insult uses a psychological
  framing; AURITY uses a clinical one. fi-core would never ship one prompt
  that fits both. The consumer owns the extraction; fi-core stores the result.
- **User profile shape** — varies wildly by domain. Discord-bot has style
  profiles, AURITY has patient profiles, a marketplace app would have a
  buyer profile. Out of scope.
- **Schema migrations** — ``PgMemoryStore.init_schema()`` ships a
  CREATE TABLE IF NOT EXISTS, but versioned migrations across time are
  the consumer's problem (alembic, sqitch, plain SQL, whatever).
"""

from fi_core.memory.protocols import MemoryStore
from fi_core.memory.retention import Default90d, RetentionPolicy
from fi_core.memory.types import ConsolidationOp, Fact, FactSource

__all__ = [
    "ConsolidationOp",
    "Default90d",
    "Fact",
    "FactSource",
    "MemoryStore",
    "RetentionPolicy",
]
