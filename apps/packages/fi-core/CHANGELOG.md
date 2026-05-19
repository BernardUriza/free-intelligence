# Changelog

All notable changes to `fi-core` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-05-19

### Added

- `fi_core.rag.DocumentChunkStore` Protocol — explicit interface for
  persistent chunk storage, decoupled from any specific backend.
- `fi_core.stores.hdf5.HDF5ChunkStore` — first concrete implementation
  of `DocumentChunkStore`, backed by HDF5 via `h5py`. Supports both
  async and sync APIs.
- New type module surface:
  - `ChunkWithEmbedding` — chunk text + its vector representation.
  - `DocumentMetadata` — document-level metadata associated with a
    chunk set.
  - `DocumentRecord` — combined record returned by store lookups.
- Optional install group `stores-hdf5` (pulls `h5py>=3.10`, `numpy>=1.24`).
- 34 new tests covering the HDF5 store and the protocol contract.

### Notes

- The core package remains zero-dependency. HDF5 is opt-in via
  `pip install fi-core[stores-hdf5]`.

## [0.2.0] — 2026-05-19

### Added

- `fi_core.persona` — character-integrity / anti-drift module
  extracted from the production Insult Discord bot.
- Three detector classes:
  - `BreakDetector` — hard identity leaks (retry-worthy).
  - `AntiPatternMonitor` — soft drift toward assistant tone (log only).
  - `ClarificationDumpDetector` — bot punting the task back at the
    user despite having context (retry with context cue).
- `sanitize()` — last-resort sentence-level cleanup when retries fail.
- `DetectionResult` dataclass — frozen value type with `clean`
  convenience flag and `severity` field for telemetry routing.
- 14 built-in pattern packs covering:
  - AI identity disclosure (`GENERIC_AI_DISCLOSURE_EN`, `..._ES`).
  - Assistant tone (`ASSISTANT_TONE_EN`, `..._ES`).
  - Therapy-speak (`THERAPY_SPEAK_EN`, `..._ES`).
  - Summarizing (`SUMMARIZING`).
  - Stage directions / roleplay drift (`STAGE_DIRECTIONS`).
  - Markdown formatting drift (`MARKDOWN_DRIFT`).
  - Moralizing (`MORALIZING_EN`, `..._ES`).
  - Over-validation (`OVER_VALIDATION_EN`, `..._ES`).
  - Clarification dump (`CLARIFICATION_DUMP_ES`).
- Convenience composite packs: `ALL_AI_DISCLOSURE`,
  `ALL_ASSISTANT_TONE`, `ALL_THERAPY_SPEAK`, `ALL_MORALIZING`,
  `ALL_OVER_VALIDATION`, `DEFAULT_EN`, `DEFAULT_ES`,
  `DEFAULT_BILINGUAL`.
- Reinforcement strings: `GENERIC_REINFORCEMENT`,
  `CONTEXT_REINFORCEMENT`, `IDENTITY_REINFORCEMENT_SUFFIX`.
- 31 new tests pinning the detector contracts and pack invariants
  (e.g. all packs contain only compiled `re.Pattern` objects, default
  composites equal the concatenation of their sources).

### Notes

- All persona detection is deterministic regex — zero LLM calls at
  detection time, zero embeddings, zero training data required.
- Bilingual EN+ES patterns are first-class peers, not afterthoughts.
- Persona-specific patterns stay in the consumer's codebase; the
  library only ships patterns that generalize across personas.

## [0.1.0] — 2026-05-19

### Added

- Initial release.
- `fi_core.rag` — chunking algorithm extracted verbatim from the
  AURITY `document_service` production code.
  - Three strategies: paragraph-aware, sentence-aware, fixed-size.
  - `ChunkingStrategy` enum and `ChunkConfig` dataclass.
  - `chunk_document(text, strategy, config) -> list[str]` entry point.
- `Embedder` Protocol — async `embed(text) -> list[float]` contract
  for any embedding backend (sentence-transformers, Azure OpenAI
  ada-002, etc.).
- `ChunkStore` Protocol — first-pass storage contract (later superseded
  by `DocumentChunkStore` in 0.3.0).
- `Chunk` and `RetrievedChunk` dataclasses for typed chunk values.
- 9 tests covering chunking behavior across strategies and edge cases.

### Notes

- Zero runtime dependencies. The package targets Python 3.12+.
- Intended consumers at extraction time: AURITY (on-prem medical) and
  the Insult Discord bot (Azure-native conversational).

[0.3.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.3.0
[0.2.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.2.0
[0.1.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.1.0
