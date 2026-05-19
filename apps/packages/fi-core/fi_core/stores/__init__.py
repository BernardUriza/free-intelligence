"""Concrete ``ChunkStore`` / ``DocumentChunkStore`` implementations.

Submodules in here ship reference implementations of the storage protocols
defined in ``fi_core.rag.protocols``. Each implementation pulls in its own
backend dependencies via optional-deps extras:

- ``fi_core.stores.hdf5`` requires ``fi-core[stores-hdf5]`` (h5py + numpy).
- ``fi_core.stores.pgvector`` requires ``fi-core[stores-pgvector]``
  (psycopg + pgvector). Coming in a follow-up release.

Importing the submodule without the optional dependencies installed
raises an informative ImportError. The base ``fi-core`` install does
NOT pull these in — keeps the core package zero-deps.
"""
