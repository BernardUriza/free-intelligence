# `StoreBackedRetriever.ingest` leaves the OLD chunks retrievable after a correction

Status: Proposed — reproduced, and the obvious fix is a silent no-op
Proposed: 2026-08-24 by Claude, during the fi-core audit pass

## What it is

`RagStore.ingest` deletes a document's chunks before writing the new ones.
`StoreBackedRetriever.ingest` (`fi_core/rag/store_retrieval.py`) only calls
`store.add`. Its docstring punts — *"idempotency is the store's responsibility"* —
but the store's idempotency key is `(namespace, source_ref, text)`, and **edited
text is a new key**. So correcting a document leaves the previous, now-wrong
version searchable forever, beside the new one.

Reproduced against the real HDF5 store:

```
ingest("La reunion es el lunes en la sala azul.",  source_ref="aviso.md")
ingest("La reunion es el martes en la sala roja.", source_ref="aviso.md")
retrieve("cuando es la reunion") -> BOTH chunks
```

A user who fixes a date gets asked to choose between Monday and Tuesday, with
nothing marking which is current.

## Why this is not a two-line patch

The obvious fix — call `delete_chunks_by_document` before adding, the way
`RagStore.ingest` does — **removes zero rows on this path**, measured:

```
delete_chunks_by_document(namespace="n", document_id="aviso.md") -> 0
```

Chunks written through `store.add` are not associated with a document record at
all; `add` takes no `document_id`. So shipping that patch would look applied,
pass a naive test, and change nothing — which is worse than the defect, because
it removes the reason to look again.

## The decision that is the owner's

Two coherent routes, and they are not equivalent:

- **Give `add` a document.** The retriever registers a document for its
  `source_ref` and writes through `save_chunks`, converging with `RagStore` on one
  write path. Most correct; touches both store implementations.
- **Add delete-by-source_ref to the protocol.** Narrower, keeps the two paths
  distinct, and admits that a "retriever" and a "store service" are different
  things — but it is a second deletion API to keep in sync.

## Related, found in the same pass

`contextual.py` is unreachable through both production faces:
`RagStore.from_components` hard-wires `StoreBackedRetriever(contextualizer=None)`,
and the only face that applies a contextualizer is the retriever nobody constructs
directly. A grep for `contextualizer` outside `fi_core/rag/` hits only fi-core's
own tests. Either wire it or freeze it — see [[migrations-end-with-deletion]].
