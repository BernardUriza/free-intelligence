# Changelog

All notable changes to `fi-core` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] — 2026-05-19

### Added

- `fi_core.stores.pgvector.PgVectorChunkStore` — second reference
  `DocumentChunkStore` implementation, backed by Postgres + pgvector.
  Designed for multi-tenant chat substrates that need concurrent writes,
  relational filters mixed with vector similarity, and transactional
  consistency. IVFFlat index (`lists=100`) by default; documented HNSW
  migration cue for >1M chunks per namespace. Codec registration is
  done via one-shot bare connection BEFORE pool construction (avoids
  the asyncpg "unknown type: vector" failure mode). 7 new tests using
  pytest-postgresql's ephemeral PG fixture.
- `fi_core.embeddings.azure_openai.AzureOpenAIEmbedder` — first
  reference `Embedder` implementation. Wraps Azure OpenAI's embeddings
  API via the openai SDK's `AsyncAzureOpenAI` client. Constructor takes
  explicit config (api_key, endpoint, deployment, api_version, dim) —
  NO env-var reading inside the package; caller's job to source
  credentials. Default `dim=1536` (text-embedding-ada-002 /
  text-embedding-3-small), parameterizable to 3072 for
  text-embedding-3-large. 14 new tests with mocked SDK calls — no
  network access in CI.
- `fi_core.embeddings.sentence_transformers.SentenceTransformersEmbedder` —
  second reference `Embedder` implementation. Loads a local
  sentence-transformers model into the host process (CPU by default;
  GPU via `device=` parameter, with auto-detect ladder
  `cuda > mps > cpu` when `device=None`). Lazy-load on first `embed()`
  call (model is NOT loaded at `__init__`). `model.encode` runs through
  `asyncio.to_thread` so it does not block the event loop. Default
  model `sentence-transformers/all-MiniLM-L6-v2` (384-dim, matches
  AURITY's fi-monitor GPU service). 8 new tests including a
  `@pytest.mark.slow` real-model load + encode test.

- `fi_core.persona.mcp_server.build_consolidation_prompt(facts, max_tokens_hint)`
  and `fi_core.persona.mcp_server.parse_consolidation_result(raw_response, facts)`
  — Shape B tools (per the canonical MCP pattern: server returns
  prompt + parser, NEVER executes LLM). Mem0-style judge consolidation
  ported verbatim from discord-bot's `insult/core/memory_consolidator.py`.
  Pairs so any consumer (insult-runner via Claude Code SDK + OAuth Max,
  AURITY's curator, fi-monitor) can run the judge call with its own
  credentials. The system prompt is byte-identical to discord-bot's
  `insult/prompts/memory_consolidator_judge.md`. Parser strips markdown
  fences, validates op shape against the input facts list, backfills
  implicit NOOPs for ids the judge omitted (never silently lose a row).
- `fi_core.persona.MCP_SERVER_NAME` and `fi_core.persona.MCP_TOOLS` —
  explicit MCP contract constants that v0.4.0 forgot to export. Lists
  all 7 tools (5 from 0.4.0 + 2 new consolidation tools). Re-exported
  from `fi_core.persona` so consumers can do
  `from fi_core.persona import MCP_SERVER_NAME, MCP_TOOLS` without
  digging into `mcp_server` internals. This closes the gap that forced
  discord-bot's `scripts/sync_capabilities.py` to AST-walk
  `mcp_server.py` as a fallback in 0.4.0.

### Changed

- `fi_core/__init__.py` updated to list the four new sub-package paths.
- `pyproject.toml`: new optional extras `stores-pgvector` (asyncpg +
  pgvector), `embeddings-azure` (openai), `embeddings-st`
  (sentence-transformers + torch). `[all]` and `[dev]` updated to
  bundle all five extras. Default `numpy` and `mcp` upper bounds also
  formalized in `[stores-hdf5]` and `[mcp]` (matching the conda recipe).
- `[tool.pytest.ini_options]` registers a `slow` marker for the heavy
  sentence-transformers real-model test, eliminating
  PytestUnknownMarkWarning at collection.

### Honest extraction notes

- `AzureOpenAIEmbedder` was a clean extraction from discord-bot's
  `insult/core/deep_memory.py` (lines 48-129). Stripped env-var
  reading, promoted dim to a constructor arg, added eager validation.
- `SentenceTransformersEmbedder` is "inspired by" not "extracted from"
  AURITY. AURITY's `monitor_client.py` is a thin HTTP client to a
  Cloudflare-tunneled GPU service; no `MonitorClientEmbedder` class
  exists. The fi-core implementation is a clean local-process
  equivalent modeled on `fi-monitor/rag_service/main.py:71` (the
  actual SentenceTransformer instantiation point in the free-
  intelligence monorepo).
- `PgVectorChunkStore` is "inspired by" not "extracted from"
  discord-bot's `deep_memory.py`. The discord-bot module is heavily
  Discord-domain (hardcoded `user_id` column, closed CHECK constraint
  on source_type, md5-based chunk dedupe, no document concept). The
  fi-core implementation preserves the schema shape, cosine query
  pattern, and IVFFlat index choice, but drops Discord-specific
  concepts and adds the full document-lifecycle layer needed by
  the `DocumentChunkStore` Protocol.

### Coverage

- 29 new tests (14 azure + 8 sentence-transformers + 7 pgvector).
- Full suite: 124 passing in 8.87s. 0 regressions.

## [0.4.0] — 2026-05-19

### Added

- `fi_core.persona.mcp_server` — MCP (Model Context Protocol) server
  exposing the persona detectors as tools that any MCP-compatible AI
  (Claude Code, Cursor, Anthropic API with MCP enabled) can call
  directly, without depending on `fi-core` as a Python package in
  its own process.
- Five tools shipped on the server:
  - `list_packs()` — discovery of atomic + composite packs with
    severity, language, and pattern count metadata.
  - `check_drift(text, packs)` — detect persona drift with matches
    grouped by severity tier (break / soft_drift / clarification_dump).
  - `sanitize_response(text, packs)` — last-resort sentence-level
    cleanup for break-severity matches.
  - `get_reinforcement(pack_name)` — return the reinforcement string
    associated with a pack. Auto-maps `clarification_dump_*` to
    `CONTEXT_REINFORCEMENT`, everything else to `GENERIC_REINFORCEMENT`.
  - `validate_and_retry_prompt(response, system_prompt, packs)` —
    one-shot atomic loop. The killer-feature tool: validates the
    response, decides per-severity whether retry is needed, and
    returns the reinforced system prompt if so. Zero client-side
    orchestration; the AI does not need a state machine.
- Composite packs (`default_bilingual`, `all_ai_disclosure`, etc.) now
  expand to their atomic components when processed by the MCP server,
  preserving per-pattern severity tier end-to-end. A hard break inside
  `default_bilingual` is routed through the break-tier detector, not
  the soft-drift one.
- 21 new tests in `test_persona_mcp.py` covering all five tools, the
  atomic-vs-composite expansion contract, unknown-pack graceful
  fallback, severity-precedence rules, and the no-retry-on-soft-drift
  decision rule.

### Changed

- `fi-core` now ships an optional `[mcp]` extra (depends on `mcp>=1.4`).
  Install as `pip install 'fi-core[mcp]'` to enable the server.
- Anaconda conda recipe `meta.yaml` keeps `mcp` as a non-required
  dependency since the base package remains usable without it; the
  conda-forge submission will declare it as optional output.

### Install + register

```bash
pip install 'fi-core[mcp]'
claude mcp add fi-core-persona -- python -m fi_core.persona.mcp_server
```

After registration, any MCP client (Claude Code, Cursor) can invoke the
five tools directly. The killer use case is the meta-validation loop:
the AI checks its own output for persona drift via `validate_and_retry_prompt`
before sending the response to the user, and retries with the right
reinforcement automatically if drift is detected.

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
