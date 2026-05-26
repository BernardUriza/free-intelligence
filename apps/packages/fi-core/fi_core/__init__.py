"""fi-core — shared primitives for AURITY + Insult.

Sub-packages:
- ``fi_core.rag``                          — chunking + Embedder / ChunkStore / DocumentChunkStore protocols
- ``fi_core.stores.hdf5``                  — h5py-backed reference DocumentChunkStore (extras: stores-hdf5)
- ``fi_core.stores.pgvector``              — Postgres + pgvector DocumentChunkStore (extras: stores-pgvector)
- ``fi_core.embeddings.azure_openai``      — Azure OpenAI Embedder (extras: embeddings-azure)
- ``fi_core.embeddings.sentence_transformers`` — local sentence-transformers Embedder (extras: embeddings-st)
- ``fi_core.persona``                      — character-integrity / anti-drift detectors and packs
- ``fi_core.persona.mcp_server``           — MCP server exposing persona detectors as AI tools (extras: mcp)
- ``fi_core.training``                     — training pipes (datasets, tokenizers, TinyGPT, PyTorchTrainer) (extras: training)
- ``fi_core.memory``                       — long-term fact memory + Mem0-style consolidator (extras: memory)
"""

__version__ = "0.24.3"
