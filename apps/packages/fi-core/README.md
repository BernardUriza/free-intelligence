# fi-core

**Free Intelligence core** — shared RAG primitives used by [AURITY](https://app.aurity.io) (on-prem medical) and [Insult discord-bot](https://github.com/BernardUriza/discord-bot) (Azure-native conversational).

## What's inside

```
fi_core/
└── rag/
    ├── chunking.py    # 3 chunking strategies (paragraph/sentence/fixed)
    ├── protocols.py   # Embedder + ChunkStore Protocol classes
    └── types.py       # Chunk dataclass
```

## Why a separate package

Both AURITY and Insult need RAG, but with different embedders (GPU sentence-transformers vs. Azure OpenAI ada-002) and different stores (HDF5 vs. pgvector). The **chunking algorithm** is identical and was already battle-tested in AURITY for medical PHI — extracting it as a shared library:

- Stops the code drift between the two codebases
- Makes the interface (Embedder, ChunkStore Protocols) explicit
- Lets either project upgrade the chunking strategy without touching the other
- Is a clean PyPI candidate once stable

## Install

Lives inside the `free-intelligence` monorepo at
`apps/packages/fi-core` (sibling of `fi-auth` and `fi-observability`).

Dev (editable, from local monorepo):

```bash
pip install -e ~/Documents/free-intelligence/apps/packages/fi-core
```

From git (once pushed, monorepo subdir):

```bash
pip install "fi-core @ git+https://github.com/BernardUriza/free-intelligence.git#subdirectory=apps/packages/fi-core"
```

From PyPI (future, when 1.0):

```bash
pip install fi-core
```

## Who uses it

- **AURITY** (free-intelligence/backend/services/document/services/document_service.py) — was the original home of the chunking code; now imports from `fi_core.rag` instead of duplicating.
- **fi-monitor rag_service** (free-intelligence/apps/fi-monitor/rag_service) — uses `fi_core.rag.chunk_document` in its upload flow.
- **Insult discord-bot** (`insult/core/deep_memory.py`) — Azure-native sibling implementation using Azure OpenAI ada-002 + pgvector.

## Usage

```python
from fi_core.rag import chunk_document, ChunkingStrategy, ChunkConfig

chunks = chunk_document(
    long_text,
    strategy=ChunkingStrategy.PARAGRAPH_AWARE,
    config=ChunkConfig(chunk_size=400, overlap=50, min_chunk_size=100),
)
# → list[str] of ~400-token chunks with 50-token overlap
```

Implement the Embedder protocol for your stack:

```python
from fi_core.rag import Embedder

class MyAzureEmbedder:
    async def embed(self, text: str) -> list[float]:
        ...

# Type-check at composition time:
embedder: Embedder = MyAzureEmbedder()
```

## Origin

The chunking module was extracted verbatim from `free-intelligence/backend/services/document/services/chunking_strategy.py` (created 2026-01-29 by Bernard + Claude Sonnet 4.5). The protocols were added when extracting (2026-05-19) to break the AURITY-specific coupling to `monitor_client` + `IDocumentRepository`.

## License

MIT.
