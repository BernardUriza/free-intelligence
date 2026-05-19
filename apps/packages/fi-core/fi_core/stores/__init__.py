"""Concrete ``ChunkStore`` / ``DocumentChunkStore`` implementations.

Submodules in here ship reference implementations of the storage protocols
defined in ``fi_core.rag.protocols``. Each implementation pulls in its own
backend dependencies via optional-deps extras:

- ``fi_core.stores.hdf5`` requires ``fi-core[stores-hdf5]`` (h5py + numpy).
  Best for single-tenant or few-tenant longitudinal scientific data with
  append-mostly write pattern. Per-namespace document tree on disk.
- ``fi_core.stores.pgvector`` requires ``fi-core[stores-pgvector]``
  (asyncpg + pgvector). Best for multi-tenant chat substrates with
  concurrent writes, relational filters mixed with vector similarity,
  and transactional consistency. IVFFlat index by default.

Both implement the same ``DocumentChunkStore`` Protocol — pick by use
case, not by abstraction layer.

Importing the submodule without the optional dependencies installed
raises an informative ImportError. The base ``fi-core`` install does
NOT pull these in — keeps the core package zero-deps.
"""
