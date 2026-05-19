# fi-core

**Free Intelligence core** — shared LLM primitives used by [AURITY](https://app.aurity.io) (on-prem medical) and [Insult discord-bot](https://github.com/BernardUriza/discord-bot) (Azure-native conversational).

Two product surfaces in one package:

- **`fi_core.rag`** — chunking algorithm + Embedder / ChunkStore protocols for retrieval-augmented generation
- **`fi_core.persona`** — character-integrity / anti-drift detectors and built-in pattern packs (English + Spanish)

## What's inside

```
fi_core/
├── rag/
│   ├── chunking.py    # 3 chunking strategies (paragraph/sentence/fixed)
│   ├── protocols.py   # Embedder + ChunkStore Protocol classes
│   └── types.py       # Chunk dataclass
└── persona/
    ├── detect.py      # BreakDetector, AntiPatternMonitor, ClarificationDumpDetector, sanitize
    ├── packs.py       # Built-in pattern packs (EN + ES) + reinforcement strings
    └── types.py       # DetectionResult dataclass
```

## Why a separate package

Both AURITY and Insult need RAG **and** care about character integrity, but with different embedders (GPU sentence-transformers vs. Azure OpenAI ada-002), different stores (HDF5 vs. pgvector), and different personas (clinical vs. conversational). The **chunking algorithm** and the **anti-drift patterns** are identical at the byte level and were already battle-tested in production — extracting them as a shared library:

- Stops the code drift between the two codebases
- Makes the interfaces (Embedder, ChunkStore, BreakDetector composition) explicit
- Lets either project upgrade independently of the other
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

## Usage — RAG

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

## Usage — Persona / anti-drift

```python
from fi_core.persona import BreakDetector, AntiPatternMonitor, sanitize, packs

# Compose a bilingual break detector with a reinforcement string
break_detector = BreakDetector(
    patterns=packs.GENERIC_AI_DISCLOSURE_EN + packs.GENERIC_AI_DISCLOSURE_ES,
    reinforcement=packs.GENERIC_REINFORCEMENT,
)

# Soft-drift monitor — log only, do not block
tone_monitor = AntiPatternMonitor(
    patterns=packs.ASSISTANT_TONE_EN + packs.STAGE_DIRECTIONS,
)

response = await llm.chat(system_prompt, messages)

# Hard break → retry with reinforcement
if break_detector.detect(response):
    response = await llm.chat(system_prompt + break_detector.reinforcement, messages)
    if break_detector.detect(response):
        # Retry also failed — last-resort sentence-level cleanup
        response = sanitize(response, patterns=break_detector.patterns)

# Soft drift → emit telemetry, send response anyway
for matched in tone_monitor.detect(response):
    telemetry.emit("persona.soft_drift", pattern=matched)
```

Available packs: `GENERIC_AI_DISCLOSURE_EN/ES`, `ASSISTANT_TONE_EN/ES`, `THERAPY_SPEAK_EN/ES`, `SUMMARIZING`, `STAGE_DIRECTIONS`, `MARKDOWN_DRIFT`, `MORALIZING_EN/ES`, `OVER_VALIDATION_EN/ES`, `CLARIFICATION_DUMP_ES`, plus convenience composites `DEFAULT_EN`, `DEFAULT_ES`, `DEFAULT_BILINGUAL`.

Persona-specific patterns (e.g. patterns unique to a single bot's character) should **stay private in the consumer's codebase** and be merged with the generic packs at composition time. The library only ships patterns that generalize across personas.

## Origin

The `rag` chunking module was extracted verbatim from `free-intelligence/backend/services/document/services/chunking_strategy.py` (created 2026-01-29 by Bernard + Claude Sonnet 4.5). The `rag` protocols were added when extracting (2026-05-19) to break the AURITY-specific coupling to `monitor_client` + `IDocumentRepository`.

The `persona` module was extracted from `discord-bot/insult/core/character/detection.py` on 2026-05-19, filtering out Insult-specific patterns so the public packs generalize across deployments.

## License

MIT.
