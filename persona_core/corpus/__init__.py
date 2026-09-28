"""Corpus retrieval — the RAG-by-namespace path is the ONLY one.

Live modules:

- ``pg_rag``: Postgres + Azure ada-002 embeddings over ``deep_memory_chunks``.
- ``references``: ``build_references_block`` — the 3 nearest chunks of a
  persona's namespace (``shared/personas/registry.py::corpus_namespace``),
  similarity floor 0.78, header from ``shared/corpus/headers/<id>.md``.

The pre-purga "universal values" frames (``animal_liberation.md``,
``animal_liberation_tactics.md`` + its in-memory ``rag.py``,
``film_criticism.md``, ``vegan_gastronomy.md``) and their topic detectors
died here on 2026-09-07 (issue #62): zero callers outside this package since
2f8d9ad, kept green only by their own tests. The content is recoverable from
git (``git show 798ba77:khimeras_shared/corpus/<file>``) as source material
for the per-persona namespaces (issue #61).
"""
