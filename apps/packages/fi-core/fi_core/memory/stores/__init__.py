"""Concrete ``MemoryStore`` implementations.

Submodules:
- ``fi_core.memory.stores.pgvector_memory`` — Postgres + pgvector impl
  extracted from discord-bot's ``FactsRepository``. Async-first via
  asyncpg, soft-delete + hard-purge + Mem0-style consolidation apply,
  optional pgvector-backed semantic search.

Importing without ``fi-core[memory]`` (asyncpg + pgvector) raises
``ImportError`` from the submodule.
"""
