"""DatasetReader backed by ``fi_core.stores.hdf5.HDF5ChunkStore``.

Streams chunks out of a previously-populated HDF5 store. The reader
takes a constructed ``HDF5ChunkStore`` instance (not a path) so the
caller controls construction, lifecycle, and concurrency wrapping.

Usage::

    from fi_core.stores.hdf5 import HDF5ChunkStore
    from fi_core.training.datasets.hdf5_reader import HDF5DatasetReader

    store = HDF5ChunkStore("/path/to/corpus.h5")
    reader = HDF5DatasetReader(store)
    async for chunk in reader.read_chunks("corpus_v1"):
        ...  # feed to tokenizer / DataLoader
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fi_core.rag.types import Chunk
    from fi_core.stores.hdf5 import HDF5ChunkStore


class HDF5DatasetReader:
    """Stream ``Chunk``s out of an ``HDF5ChunkStore``.

    Iterates documents in the namespace (any status) and yields each
    document's chunks in store-defined order. The total chunk count
    available is reported by :meth:`count`.
    """

    def __init__(self, store: HDF5ChunkStore) -> None:
        self._store = store

    async def read_chunks(
        self,
        namespace: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Chunk]:
        documents = await self._store.list_documents(namespace=namespace)
        yielded = 0
        for doc in documents:
            chunks = await self._store.get_chunks_by_document(
                namespace=namespace, document_id=doc.document_id
            )
            for chunk in chunks:
                if limit is not None and yielded >= limit:
                    return
                yield chunk
                yielded += 1

    async def count(self, namespace: str) -> int:
        documents = await self._store.list_documents(namespace=namespace)
        total = 0
        for doc in documents:
            chunks = await self._store.get_chunks_by_document(
                namespace=namespace, document_id=doc.document_id
            )
            total += len(chunks)
        return total
