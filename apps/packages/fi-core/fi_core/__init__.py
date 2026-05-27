"""fi-core — Free Intelligence shared primitives.

fi-core is a zero-dep core of building blocks consumed by every Free
Intelligence runtime (fi-runner-based agents: ALICE, Ferboli, Insult-AI,
plus any future consumer). It bundles RAG primitives, personas / anti-
drift detectors, embedders, document stores, training pipes, and long-
term memory — exposed as a flat namespace of typed Protocols + reference
implementations.

The core (``fi_core``) is dep-free. Heavy dependencies live behind
``[project.optional-dependencies]`` extras::

    pip install fi-core                   # bare protocols + types
    pip install "fi-core[stores-hdf5]"    # HDF5 DocumentChunkStore
    pip install "fi-core[stores-pgvector]"# Postgres + pgvector store
    pip install "fi-core[embeddings-azure]"   # Azure OpenAI embedder
    pip install "fi-core[embeddings-st]"  # sentence-transformers embedder
    pip install "fi-core[rerank]"         # BAAI/bge cross-encoder reranker
    pip install "fi-core[training]"       # TinyGPT + PyTorchTrainer + tokenizers
    pip install "fi-core[memory]"         # PgMemoryStore + FactConsolidator
    pip install "fi-core[mcp]"            # MCP servers exposing fi-core as tools
    pip install "fi-core[cognitive]"      # clinical cognitive-flow presets (YAML)

Sub-packages:

- ``fi_core.rag``                — chunking + ``Embedder`` / ``ChunkStore`` / ``DocumentChunkStore`` protocols (dep-free)
- ``fi_core.stores.hdf5``        — h5py-backed reference ``DocumentChunkStore`` (extra: stores-hdf5)
- ``fi_core.stores.pgvector``    — Postgres + pgvector ``DocumentChunkStore`` (extra: stores-pgvector)
- ``fi_core.embeddings.azure_openai`` — Azure OpenAI Embedder (extra: embeddings-azure)
- ``fi_core.embeddings.sentence_transformers`` — local sentence-transformers Embedder (extra: embeddings-st)
- ``fi_core.persona``            — character-integrity / anti-drift detectors and pattern packs (dep-free)
- ``fi_core.persona.mcp_server`` — MCP server exposing persona detectors as AI tools (extra: mcp)
- ``fi_core.cognitive``          — clinical cognitive-flow primitives (urgency triage, SOAP, FSM, presets)
- ``fi_core.training``           — training pipes (datasets, tokenizers, TinyGPT, PyTorchTrainer) (extra: training)
- ``fi_core.memory``             — long-term fact memory + Mem0-style consolidator (extra: memory)
- ``fi_core.task_tracker``       — agent plan-tracking primitives + MCP server (extra: mcp)

Importing ``fi_core`` directly is cheap: this ``__init__`` only sets
``__version__``. Submodules load on demand when a consumer writes
``from fi_core.persona import …`` or similar — heavy SDK deps (h5py,
torch, openai, etc.) never load unless their extra is actually used.
"""

__version__ = "0.24.4"

__all__ = ["__version__"]
