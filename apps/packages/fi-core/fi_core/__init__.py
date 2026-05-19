"""fi-core — shared primitives for AURITY + Insult.

Sub-packages:
- ``fi_core.rag``               — chunking + Embedder / ChunkStore / DocumentChunkStore protocols
- ``fi_core.stores.hdf5``       — h5py-backed reference DocumentChunkStore (extras: stores-hdf5)
- ``fi_core.persona``           — character-integrity / anti-drift detectors and packs
- ``fi_core.persona.mcp_server``— MCP server exposing persona detectors as AI tools (extras: mcp)
"""

__version__ = "0.4.0"
