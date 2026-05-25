"""Concrete ``Embedder`` implementations.

Submodules in here ship reference implementations of the ``Embedder``
protocol defined in ``fi_core.rag.protocols``. Each implementation
pulls in its own backend dependencies via optional-deps extras:

- ``fi_core.embeddings.azure_openai`` requires ``fi-core[embeddings-azure]``
  (the ``openai`` SDK with AsyncAzureOpenAI support).
- ``fi_core.embeddings.sentence_transformers`` requires
  ``fi-core[embeddings-st]`` (sentence-transformers + torch).

Importing the submodule without its backend dependencies raises an
informative ``ImportError``. The base ``fi-core`` install does NOT
pull either in — keeps the core package zero-deps.

``HashingEmbedder`` (feature hashing) is the exception: zero-model and
dep-free, so it lives in the base install and is re-exported here.
"""

from fi_core.embeddings.hashing import HashingEmbedder

__all__ = ["HashingEmbedder"]
