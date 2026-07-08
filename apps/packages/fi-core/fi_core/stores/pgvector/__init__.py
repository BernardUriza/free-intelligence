"""Postgres + pgvector-backed implementation of ``DocumentChunkStore``.

Reference implementation of the storage protocol defined in
``fi_core.rag.protocols.DocumentChunkStore``, backed by PostgreSQL with
the ``pgvector`` extension. Designed for multi-tenant chat substrates
and similar workloads where relational filters (namespace, status,
attribute) combine with vector similarity at query time.

Use case vs the HDF5 sibling:

- **Concurrent writers**: Postgres handles them natively; the HDF5 store
  is single-writer per file. Pick this implementation when you have
  multiple processes ingesting into the same logical store.
- **Transactional consistency**: ``save_chunks`` runs in one
  transaction; cascading delete rolls back atomically on failure.
- **Operational cost**: heavier than HDF5 — needs a Postgres server,
  the ``vector`` extension installed (Azure Flexible Server enables it
  via ``azure.extensions=VECTOR``; self-hosted needs the ``pgvector``
  package + ``CREATE EXTENSION vector``), and a connection pool.

Package layout:

- ``store``  — the ``PgVectorChunkStore`` class (protocol surface)
- ``schema`` — parametrized DDL (tables, indexes, IVFFlat choice)
- ``rows``   — asyncpg Record → domain-type mapping

Shared substrate: connection bootstrap lives in ``fi_core.stores._pg``
(also consumed by ``fi_core.memory.stores.pgvector_memory``); chunk-id
derivation in ``fi_core.stores._common`` (shared with the HDF5 sibling).

N (the embedding dimension) is parameterized at construction time and
locked at schema-init. Cosine similarity uses pgvector's ``<=>``
operator (smaller-is-closer); the returned ``similarity`` is
``1 - distance`` so the value is in [0, 1] across stores.

Optional dependency: ``asyncpg`` + ``pgvector``. Install via
``pip install 'fi-core[stores-pgvector]'``.
"""

from fi_core.stores.pgvector.store import PgVectorChunkStore

__all__ = ["PgVectorChunkStore"]
