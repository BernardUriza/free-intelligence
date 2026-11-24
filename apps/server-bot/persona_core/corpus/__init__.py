"""Corpus retrieval over ``corpus_chunks``, one namespace per persona.

- ``pg_rag``: Postgres, local multilingual e5 embeddings, cross-encoder reranker.
- ``references``: the topical lane, gated by relevance.
- ``style``: the voice lane, a random draw of real lines for register.
- ``ingest``: the manifest and the sync that make a namespace match it.
- ``rules`` + ``rules.yml``: every threshold both lanes use.
"""
