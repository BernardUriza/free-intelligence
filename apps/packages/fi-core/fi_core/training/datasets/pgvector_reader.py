"""DatasetReader backed by ``fi_core.stores.pgvector.PgVectorChunkStore``.

Streams chunks out of a Postgres + pgvector store. The reader takes a
constructed ``PgVectorChunkStore`` instance (not a DSN string) so the
caller controls pool lifecycle and credential sourcing.

Usage::

    from fi_core.stores.pgvector import PgVectorChunkStore
    from fi_core.training.datasets.pgvector_reader import PgVectorDatasetReader

    store = PgVectorChunkStore(dsn="postgresql://...")
    await store.init_schema()
    reader = PgVectorDatasetReader(store)
    async for chunk in reader.read_chunks("corpus_v1"):
        ...  # feed to tokenizer / DataLoader

The reader does NOT manage the store's pool — call ``await store.close()``
separately when you're done.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fi_core.rag.types import Chunk
    from fi_core.stores.pgvector import PgVectorChunkStore


class PgVectorDatasetReader:
    """Stream ``Chunk``s out of a ``PgVectorChunkStore``.

    Iterates documents in the namespace (any status) and yields each
    document's chunks in DB-defined order (typically chunk_index ASC).
    The total chunk count available is reported by :meth:`count`.
    """

    def __init__(self, store: PgVectorChunkStore) -> None:
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
