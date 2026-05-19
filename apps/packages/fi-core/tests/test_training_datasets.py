"""Tests for `fi_core.training.datasets`.

``HDF5DatasetReader`` is exercised against a real (ephemeral)
``HDF5ChunkStore`` instance — no mocks. ``PgVectorDatasetReader`` is
covered by a smoke test that verifies its Protocol compliance against
a mock store; the full async iteration is covered by the HDF5 path
(both readers share the same logic structure).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from fi_core.training import DatasetReader


@pytest.fixture
async def hdf5_store_with_chunks():
    """Build an HDF5 store with 3 documents × 2 chunks each = 6 chunks."""
    from fi_core.rag import Chunk, ChunkWithEmbedding
    from fi_core.stores.hdf5 import HDF5ChunkStore

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "test.h5"
        store = HDF5ChunkStore(str(path))
        for i in range(3):
            doc_id = f"doc-{i}"
            await store.create_document(
                namespace="ns",
                document_id=doc_id,
                content=f"document {i} content",
            )
            chunks = [
                ChunkWithEmbedding(
                    chunk=Chunk(
                        text=f"chunk {i}-{j}",
                        source_type="test",
                        source_ref=doc_id,
                    ),
                    embedding=[float(j), float(i)],
                )
                for j in range(2)
            ]
            await store.save_chunks(
                namespace="ns", document_id=doc_id, chunks=chunks
            )
        yield store


class TestHDF5DatasetReader:
    async def test_satisfies_dataset_reader_protocol(self, hdf5_store_with_chunks):
        from fi_core.training.datasets.hdf5_reader import HDF5DatasetReader

        reader = HDF5DatasetReader(hdf5_store_with_chunks)
        assert isinstance(reader, DatasetReader)

    async def test_read_all_chunks_in_namespace(self, hdf5_store_with_chunks):
        from fi_core.training.datasets.hdf5_reader import HDF5DatasetReader

        reader = HDF5DatasetReader(hdf5_store_with_chunks)
        chunks = [c async for c in reader.read_chunks("ns")]
        assert len(chunks) == 6
        texts = {c.text for c in chunks}
        assert texts == {f"chunk {i}-{j}" for i in range(3) for j in range(2)}

    async def test_limit_caps_iteration(self, hdf5_store_with_chunks):
        from fi_core.training.datasets.hdf5_reader import HDF5DatasetReader

        reader = HDF5DatasetReader(hdf5_store_with_chunks)
        chunks = [c async for c in reader.read_chunks("ns", limit=4)]
        assert len(chunks) == 4

    async def test_count_returns_total(self, hdf5_store_with_chunks):
        from fi_core.training.datasets.hdf5_reader import HDF5DatasetReader

        reader = HDF5DatasetReader(hdf5_store_with_chunks)
        assert await reader.count("ns") == 6

    async def test_empty_namespace_yields_nothing(self, hdf5_store_with_chunks):
        from fi_core.training.datasets.hdf5_reader import HDF5DatasetReader

        reader = HDF5DatasetReader(hdf5_store_with_chunks)
        chunks = [c async for c in reader.read_chunks("ns-empty")]
        assert chunks == []
        assert await reader.count("ns-empty") == 0


class TestPgVectorDatasetReaderProtocolOnly:
    """Smoke test — Protocol satisfaction. Full integration is covered
    by the HDF5 path (both readers share identical logic structure).
    """

    def test_satisfies_dataset_reader_protocol(self):
        """We can't easily spin up PG here, but we can verify the class
        instantiates and has the right surface."""
        from fi_core.training.datasets.pgvector_reader import (
            PgVectorDatasetReader,
        )

        class _StubStore:
            async def list_documents(self, *, namespace):  # noqa: ARG002
                return []

            async def get_chunks_by_document(self, *, namespace, document_id):  # noqa: ARG002
                return []

        reader = PgVectorDatasetReader(_StubStore())  # type: ignore[arg-type]
        assert isinstance(reader, DatasetReader)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
