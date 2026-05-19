"""``DatasetReader`` implementations for ``fi_core.training``.

Submodules:
- ``fi_core.training.datasets.hdf5_reader``     — reads from ``HDF5ChunkStore``
- ``fi_core.training.datasets.pgvector_reader`` — reads from ``PgVectorChunkStore``

Each implementation pulls the corresponding store's optional deps via
``fi-core[stores-hdf5]`` or ``fi-core[stores-pgvector]``. Importing the
submodule without those installed raises ``ImportError``.
"""
